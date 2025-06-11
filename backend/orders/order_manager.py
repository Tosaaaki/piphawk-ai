import requests
from backend.utils import env_loader
from backend.utils.http_client import request_with_retries
from backend.logs.log_manager import log_trade, log_error
from backend.logs.info_logger import info
from backend.logs.trade_logger import ExitReason
from backend.logs.update_oanda_trades import fetch_trade_details
from backend.utils.price import format_price
from backend.risk_manager import (
    validate_rrr,
    validate_rrr_after_cost,
    validate_sl,
)
from risk.tp_sl_manager import adjust_sl_for_rr
from datetime import datetime, timedelta, timezone
import time
import json
import logging
import uuid

logger = logging.getLogger(__name__)

OANDA_API_URL = env_loader.get_env("OANDA_API_URL", "https://api-fxtrade.oanda.com/v3")
OANDA_ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
OANDA_API_KEY = env_loader.get_env("OANDA_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json",
}

try:
    _SESSION = requests.Session()
except Exception:
    # モック環境向けに Session が存在しない場合はダミーを使用
    _SESSION = object()

# リトライ設定（最大試行回数と待機時間上限）を環境変数で調整可能にする
HTTP_MAX_RETRIES = int(env_loader.get_env("HTTP_MAX_RETRIES", "3"))
HTTP_BACKOFF_CAP_SEC = int(env_loader.get_env("HTTP_BACKOFF_CAP_SEC", "8"))

# HTTPタイムアウト秒数を環境変数で設定（デフォルト10秒）
HTTP_TIMEOUT_SEC = int(env_loader.get_env("HTTP_TIMEOUT_SEC", "10"))

_ORDER_TEMPLATE = {
    "order": {
        "timeInForce": "FOK",
        "type": "MARKET",
        "positionFill": "DEFAULT",
    }
}


def _extract_error_details(response) -> tuple[str | None, str | None]:
    """Extract errorCode and errorMessage from a requests.Response."""
    try:
        data = response.json()
        return data.get("errorCode"), data.get("errorMessage")
    except Exception:
        return None, None


# ----------------------------------------------------------------------
#  Pip‑size table (extend as needed) and helper
# ----------------------------------------------------------------------
DEFAULT_PAIR = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")

PIP_SIZES: dict[str, float] = {
    "USD_JPY": 0.01,
    "EUR_USD": 0.0001,
    # add more pairs here if necessary
}


def get_pip_size(instrument: str) -> float:
    """Return pip size (JPY pairs use 0.01, others 0.0001)."""
    return 0.01 if instrument.endswith("_JPY") else 0.0001


class OrderManager:

    def _request_with_retries(self, method: str, url: str, **kwargs) -> object:
        """``backend.utils.http_client`` のラッパー"""
        return request_with_retries(
            method,
            url,
            headers=kwargs.pop("headers", HEADERS),
            timeout=kwargs.pop("timeout", HTTP_TIMEOUT_SEC),
            **kwargs,
        )

    # ------------------------------------------------------------------
    # LIMIT order helpers
    # ------------------------------------------------------------------
    def place_limit_order(
        self,
        instrument: str,
        units: int,
        limit_price: float,
        tp_pips: int | None = None,
        sl_pips: int | None = None,
        side: str = "long",
        entry_uuid: str | None = None,
        valid_sec: int = 180,
        risk_info: dict | None = None,
        exec_mode: str = "auto",
    ) -> dict:
        """
        Submit a LIMIT order with optional TP/SL. Returns API JSON.
        """
        pip = get_pip_size(instrument)
        tp_price = sl_price = None
        if tp_pips and sl_pips:
            if side == "long":
                tp_price = limit_price + tp_pips * pip
                sl_price = limit_price - sl_pips * pip
            else:
                tp_price = limit_price - tp_pips * pip
                sl_price = limit_price + sl_pips * pip

        comment_dict = {
            "entry_uuid": entry_uuid,
            "order_type": "limit",
            "mode": exec_mode,
        }
        if risk_info:
            comment_dict.update(
                tp=risk_info.get("tp_pips"),
                sl=risk_info.get("sl_pips"),
                pp=risk_info.get("tp_prob"),
                qp=risk_info.get("sl_prob"),
            )
        comment_json = json.dumps(comment_dict, separators=(",", ":"))
        if len(comment_json.encode("utf-8")) > 240:
            comment_json = comment_json.encode("utf-8")[:240].decode("utf-8", "ignore")

        tag = str(int(time.time()))

        payload = {
            "order": {
                "units": str(units),
                "price": format_price(instrument, limit_price),
                "instrument": instrument,
                "timeInForce": "GTD",
                "type": "LIMIT",
                "positionFill": "DEFAULT",
                "clientExtensions": {"comment": comment_json, "tag": tag},
                "gtdTime": (datetime.now(timezone.utc) + timedelta(seconds=valid_sec)).isoformat(
                    "T"
                )
                + "Z",
            }
        }
        if tp_price and sl_price:
            payload["order"]["takeProfitOnFill"] = {
                "price": format_price(instrument, tp_price),
                "timeInForce": "GTC",
            }
            payload["order"]["stopLossOnFill"] = {
                "price": format_price(instrument, sl_price),
                "timeInForce": "GTC",
            }

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        r = self._request_with_retries("post", url, json=payload)
        if not r.ok:
            code, msg = _extract_error_details(r)
            log_error(
                "order_manager",
                f"Limit order failed: {code} {msg}",
                r.text,
            )
            logger.error("Limit order failed: %s %s", r.status_code, r.text)
            r.raise_for_status()
        return r.json()

    def cancel_order(self, order_id: str) -> dict:
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{order_id}/cancel"
        r = self._request_with_retries("put", url)
        if not r.ok:
            code, msg = _extract_error_details(r)
            log_error(
                "order_manager",
                f"Cancel order failed: {code} {msg}",
                r.text,
            )
            r.raise_for_status()
        return r.json()

    def modify_order_price(
        self, order_id: str, instrument: str, new_price: float, valid_sec: int = 180
    ) -> dict:
        payload = {
            "order": {
                "price": format_price(instrument, new_price),
                "gtdTime": (datetime.now(timezone.utc) + timedelta(seconds=valid_sec)).isoformat(
                    "T"
                )
                + "Z",
            }
        }
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{order_id}"
        r = self._request_with_retries("put", url, json=payload)
        if not r.ok:
            code, msg = _extract_error_details(r)
            log_error(
                "order_manager",
                f"Modify order price failed: {code} {msg}",
                r.text,
            )
            r.raise_for_status()
        return r.json()

    def get_open_orders(self, instrument: str, side: str) -> list[dict]:
        """指定銘柄かつサイド一致するPENDING注文を取得する。"""
        url = (
            f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
            f"?state=PENDING&instrument={instrument}"
        )
        try:
            r = self._request_with_retries("get", url)
            r.raise_for_status()
            orders = r.json().get("orders", [])
        except Exception as exc:  # pragma: no cover - 通信失敗時は空リスト
            logger.warning(f"get_open_orders failed: {exc}")
            return []

        sign = 1 if side == "long" else -1
        result = []
        for od in orders:
            try:
                units = int(float(od.get("units", "0")))
                if units * sign > 0:
                    result.append(od)
            except Exception:
                continue
        return result

    def place_market_order(
        self,
        instrument,
        units,
        comment_json: str | None = None,
        price_bound: float | None = None,
    ):
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        tag = str(int(time.time()))
        order = dict(_ORDER_TEMPLATE["order"])
        order.update({
            "units": str(units),
            "instrument": instrument,
            "clientExtensions": {"tag": tag},
        })
        if comment_json:
            order["clientExtensions"]["comment"] = comment_json
        if price_bound is not None:
            order["priceBound"] = format_price(instrument, price_bound)
        data = {"order": order}
        logger.debug(f"[DEBUG] place_market_order body: {data}")
        response = self._request_with_retries("post", url, json=data)
        logger.debug(f"Market order response: {response.status_code} {response.text}")
        if response.status_code != 201:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to place order: {code} {msg}",
                response.text,
            )
            raise Exception(f"Failed to place order: {response.text}")
        return response.json()

    def place_market_with_tp_sl(
        self,
        instrument: str,
        units: int,
        side: str,
        tp_pips: float,
        sl_pips: float,
        comment_json: str | None = None,
        price_bound: float | None = None,
    ) -> dict:
        """Place a market order and immediately attach TP/SL."""
        res = self.place_market_order(
            instrument,
            units,
            comment_json=comment_json,
            price_bound=price_bound,
        )
        trade_id = (
            res.get("orderFillTransaction", {})
            .get("tradeOpened", {})
            .get("tradeID")
        )
        if not trade_id:
            return res
        price = float(res.get("orderFillTransaction", {}).get("price", 0.0))
        pip = get_pip_size(instrument)
        tp_price = (
            price + tp_pips * pip if side == "long" else price - tp_pips * pip
        )
        sl_price = (
            price - sl_pips * pip if side == "long" else price + sl_pips * pip
        )
        logger.debug(
            f"\u25b6\u25b6\u25b6 PLACE_MARKET_WITH_TPSL trade_id={trade_id} tp={tp_price} sl={sl_price}"
        )
        self.adjust_tp_sl(instrument, trade_id, new_tp=tp_price, new_sl=sl_price)
        return res

    def adjust_tp_sl(
        self,
        instrument,
        trade_id,
        new_tp=None,
        new_sl=None,
        *,
        entry_uuid: str | None = None,
    ):
        """Adjust TP/SL for a trade and store entry_uuid in comment if given."""
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        results = {}

        if new_tp is not None:
            tp_payload = {
                "order": {
                    "type": "TAKE_PROFIT",
                    "tradeID": trade_id,
                    "price": format_price(instrument, new_tp),
                    "timeInForce": "GTC",
                }
            }
            if entry_uuid:
                tp_payload["order"]["clientExtensions"] = {"comment": entry_uuid}
            logger.debug(
                f"\u25b6\u25b6\u25b6 ADJUST_TP_SL TP payload: {tp_payload}"
            )

        if new_tp is not None:
            for attempt in range(3):

                response = self._request_with_retries("put", url, json=tp_payload)

                if response.status_code == 200:
                    results["tp"] = response.json()
                    break

                code, msg = _extract_error_details(response)
                err_msg = f"TP adjustment failed: {code} {msg}"

                if code in ("NO_SUCH_TRADE", "ORDER_DOESNT_EXIST") or (
                    "NO_SUCH_TRADE" in response.text
                    or "ORDER_DOESNT_EXIST" in response.text
                ):
                    log_error("order_manager", err_msg, response.text)
                    break

                if attempt == 2:
                    log_error("order_manager", err_msg, response.text)
                time.sleep(1)

        if new_sl is not None:
            logger.debug(
                f"\u25b6\u25b6\u25b6 ADJUST_TP_SL calling update_trade_sl: {trade_id} -> {new_sl}"
            )
            sl_result = self.update_trade_sl(trade_id, instrument, new_sl)
            if sl_result is not None:
                results["sl"] = sl_result

        return results if results else None

    def get_current_tp(self, trade_id: str) -> float | None:
        """現在設定されているTP価格を取得する。"""
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}"
        try:

            resp = self._request_with_retries("get", url)
            resp.raise_for_status()
            data = resp.json()
            tp_id = data.get("trade", {}).get("takeProfitOrderID")
            if tp_id:
                order_url = (
                    f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{tp_id}"
                )

                order_resp = self._request_with_retries("get", order_url)
                order_resp.raise_for_status()
                order_data = order_resp.json()
                order_info = order_data.get("order") or order_data.get(
                    "takeProfitOrder"
                )
                if isinstance(order_info, dict):
                    price = order_info.get("price")
                    if price is not None:
                        return float(price)
        except Exception as exc:
            logger.warning(f"get_current_tp failed for {trade_id}: {exc}")
        return None

    def get_current_trailing_distance(
        self, trade_id: str, instrument: str
    ) -> float | None:
        """現在設定されているトレーリングストップ距離(pips)を取得する。"""
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}"
        try:

            resp = self._request_with_retries("get", url)

            resp.raise_for_status()
            data = resp.json()
            ts_id = data.get("trade", {}).get("trailingStopLossOrderID")
            if ts_id:
                order_url = (
                    f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{ts_id}"
                )

                order_resp = self._request_with_retries("get", order_url)

                order_resp.raise_for_status()
                order_data = order_resp.json()
                order_info = order_data.get("order") or order_data.get(
                    "trailingStopLossOrder"
                )
                if isinstance(order_info, dict):
                    dist = order_info.get("distance")
                    if dist is not None:
                        pip_factor = 0.01 if instrument.endswith("JPY") else 0.0001
                        return float(dist) / pip_factor
        except Exception as exc:
            logger.warning(
                f"get_current_trailing_distance failed for {trade_id}: {exc}"
            )
        return None

    def market_close_position(self, instrument):
        # delegate to unified close_position() helper
        logger.debug(f"[market_close_position] closing BOTH sides for {instrument}")
        return self.close_position(instrument, side="both")

    def enter_trade(
        self,
        lot_size,
        market_data,
        strategy_params,
        side="long",
        force_limit_only: bool = False,
        *,
        with_oco: bool = True,
    ):
        min_lot = float(env_loader.get_env("MIN_TRADE_LOT", "0.01"))
        max_lot = float(env_loader.get_env("MAX_TRADE_LOT", "0.1"))
        lot_size = max(min_lot, min(lot_size, max_lot))

        mode = strategy_params.get("mode", "market")
        limit_price = strategy_params.get("limit_price")
        if force_limit_only and mode == "market" and limit_price is not None:
            logger.debug(
                "[enter_trade] force_limit_only=True → converting market to limit"
            )
            mode = "limit"
        entry_uuid = strategy_params.get("entry_uuid") or str(uuid.uuid4())[:8]
        valid_sec = int(
            strategy_params.get("valid_for_sec", env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))
        )

        instrument = strategy_params["instrument"]
        tp_pips = strategy_params.get("tp_pips")
        sl_pips = strategy_params.get("sl_pips")
        pip = get_pip_size(instrument)
        # side = strategy_params.get("side", "long").lower()

        min_rrr = float(env_loader.get_env("MIN_RRR", "0.8"))
        if tp_pips is not None and sl_pips is not None:
            try:
                tp_pips, sl_pips = adjust_sl_for_rr(
                    float(tp_pips), float(sl_pips), min_rrr
                )
            except Exception:
                pass

        bid = float(market_data["prices"][0]["bids"][0]["price"])
        ask = float(market_data["prices"][0]["asks"][0]["price"])
        entry_price = bid if side == "long" else ask

        if tp_pips is not None and sl_pips is not None:
            try:
                spread_pips = (ask - bid) / pip
                slip = float(env_loader.get_env("ENTRY_SLIPPAGE_PIPS", "0"))
                min_rrr_cost = float(env_loader.get_env("MIN_RRR_AFTER_COST", "1.2"))
                if not validate_rrr_after_cost(float(tp_pips), float(sl_pips), spread_pips + slip, min_rrr_cost):
                    logger.warning(
                        "RRR after cost %.2f below %.2f – aborting entry",
                        (float(tp_pips) - (spread_pips + slip)) / float(sl_pips) if sl_pips else 0,
                        min_rrr_cost,
                    )
                    return None
            except Exception:
                pass

        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_time = datetime.now(timezone.utc).isoformat()

        rrr = None
        try:
            if tp_pips is not None and sl_pips not in (None, 0):
                rrr = float(tp_pips) / float(sl_pips)
        except Exception:
            rrr = None

        # ---- LIMIT order path ----
        if mode == "limit":
            return self.place_limit_order(
                instrument=instrument,
                units=units,
                limit_price=limit_price,
                tp_pips=tp_pips,
                sl_pips=sl_pips,
                side=side,
                entry_uuid=entry_uuid,
                valid_sec=valid_sec,
                risk_info=strategy_params.get("risk"),
                exec_mode=strategy_params.get("exec_mode", "auto"),
            )

        # ---- embed entry‑regime JSON into clientExtensions.comment (≤255 bytes) ----
        comment_json = None
        try:
            regime_info = strategy_params.get("market_cond", {}) or {}
            comment_dict = {
                "regime": regime_info.get("market_condition"),
                "dir": regime_info.get("trend_direction"),
                "order_type": mode,
                "mode": strategy_params.get("exec_mode", "auto"),
                "entry_uuid": entry_uuid,
            }
            # ---- embed AI risk info (tp/sl & probabilities) if present ----
            risk_info = strategy_params.get("risk", {})
            if risk_info:
                comment_dict.update(
                    tp=risk_info.get("tp_pips"),
                    sl=risk_info.get("sl_pips"),
                    pp=risk_info.get("tp_prob"),  # TP probability
                    qp=risk_info.get("sl_prob"),  # SL probability
                )
            comment_json = json.dumps(comment_dict, separators=(",", ":"))
            # OANDA は 255 byte 制限。安全マージンで 240 byte に丸める
            if len(comment_json.encode("utf-8")) > 240:
                comment_json = comment_json.encode("utf-8")[:240].decode(
                    "utf-8", "ignore"
                )
        except Exception as exc:
            logger.debug(f"[enter_trade] building comment JSON failed: {exc}")

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        tag = str(int(time.time()))
        client_ext = {"tag": tag}
        if comment_json:
            client_ext["comment"] = comment_json
        order_body = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
                "clientExtensions": client_ext,
            }
        }

        price_bound_pips = float(env_loader.get_env("PRICE_BOUND_PIPS", "0"))
        if price_bound_pips > 0:
            try:
                if side == "long":
                    bound = ask + price_bound_pips * pip
                else:
                    bound = bid - price_bound_pips * pip
                order_body["order"]["priceBound"] = format_price(instrument, bound)
            except Exception:
                pass

        if with_oco and tp_pips and sl_pips:
            if side == "long":
                tp_price = entry_price + float(tp_pips) * pip
                sl_price = entry_price - float(sl_pips) * pip
            else:
                tp_price = entry_price - float(tp_pips) * pip
                sl_price = entry_price + float(sl_pips) * pip

            order_body["order"]["takeProfitOnFill"] = {
                "price": format_price(instrument, tp_price),
                "timeInForce": "GTC",
            }
            order_body["order"]["stopLossOnFill"] = {
                "price": format_price(instrument, sl_price),
                "timeInForce": "GTC",
            }

        response = self._request_with_retries("post", url, json=order_body)

        logger.debug(
            f"Order placement response: {response.status_code} - {response.text}"
        )
        if response.status_code != 201:
            raise Exception(f"Failed to place order: {response.text}")

        result = response.json()
        # Save market regime at entry (if provided)
        entry_regime = None
        if strategy_params.get("market_cond"):
            entry_regime = json.dumps(strategy_params["market_cond"])
        log_trade(
            instrument=instrument,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            ai_reason=strategy_params.get("ai_reason", "manual"),
            ai_response=strategy_params.get("ai_response"),
            entry_regime=entry_regime,
            tp_pips=tp_pips,
            sl_pips=sl_pips,
            rrr=rrr,
            is_manual=False,
        )
        info(
            "entry",
            pair=instrument,
            side=side,
            id=result.get("orderFillTransaction", {}).get("id"),
            price=entry_price,
            lot=lot_size,
            regime=(strategy_params.get("market_cond") or {}).get("market_condition"),
        )

        # --- もし TP/SL が付いていない場合は再設定する ---------------------
        if with_oco and tp_pips and sl_pips:
            trade_id = (
                result.get("orderFillTransaction", {})
                .get("tradeOpened", {})
                .get("tradeID")
            )
            if trade_id and hasattr(self, "get_current_tp"):
                time.sleep(1)
                try:
                    current_tp = self.get_current_tp(trade_id)
                except Exception:
                    current_tp = None
                if current_tp is None:
                    tp_price = (
                        entry_price + float(tp_pips) * pip
                        if side == "long"
                        else entry_price - float(tp_pips) * pip
                    )
                    sl_price = (
                        entry_price - float(sl_pips) * pip
                        if side == "long"
                        else entry_price + float(sl_pips) * pip
                    )
                    try:
                        self.adjust_tp_sl(
                            instrument,
                            trade_id,
                            new_tp=tp_price,
                            new_sl=sl_price,
                        )
                        logger.info(f"Reattached TP/SL for trade {trade_id}")
                    except Exception as exc:
                        logger.warning(f"TP/SL reattach failed: {exc}")

        return result

    def exit_trade(self, position):
        instrument = position["instrument"]
        units_val = float(position.get("units", 0))
        # log raw position info before side detection
        logger.debug(f"[exit_trade] raw units={units_val} position={position}")

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}"

        response = self._request_with_retries("get", url)
        if response.status_code != 200:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to fetch position details: {code} {msg}",
                response.text,
            )
            raise Exception(f"Failed to fetch position details: {response.text}")

        position_data = response.json()["position"]
        long_units = int(position_data["long"]["units"])
        short_units = int(position_data["short"]["units"])

        if short_units < 0:
            side = "short"
        elif long_units > 0:
            side = "long"
        else:
            side = "both"

        logger.debug(f"[exit_trade] API-based detected side={side} for {instrument}")
        result = self.close_position(instrument, side)

        entry_price = float(
            position["long"]["averagePrice"]
            if int(position["long"]["units"]) > 0
            else position["short"]["averagePrice"]
        )

        if side == "long":
            units = int(position["long"]["units"])
        elif side == "short":
            units = int(position["short"]["units"])
        else:
            units = 0

        log_trade(
            instrument=instrument,
            entry_time=position.get("entry_time", datetime.now(timezone.utc).isoformat()),
            entry_price=entry_price,
            units=units,
            ai_reason="exit",
            exit_time=datetime.now(timezone.utc).isoformat(),
            exit_reason=ExitReason.MANUAL,
            is_manual=True,
        )
        info(
            "exit",
            pair=instrument,
            reason="MANUAL",
            price=entry_price,
            pnl=position.get("pl"),
        )
        return result

    def close_position(self, instrument, side: str = "both"):
        if side is None:
            raise ValueError("side must be 'long', 'short', or 'both'")
        url = (
            f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}/close"
        )

        # OANDA spec: we must explicitly specify which side(s) to close
        if side == "short":
            payload = {"shortUnits": "ALL"}
        elif side == "long":
            payload = {"longUnits": "ALL"}
        else:
            # close both sides explicitly
            payload = {"longUnits": "ALL", "shortUnits": "ALL"}

        logger.debug(f"[close_position] payload={payload}")

        response = self._request_with_retries("put", url, json=payload)

        if not response.ok:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to close position: {code} {msg}",
                response.text,
            )
            raise Exception(f"Failed to close position: {response.text}")

        return response.json()

    def close_partial(self, trade_id: str, units: int) -> dict:
        """Close a portion of a trade by specifying units."""
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}/close"
        payload = {"units": str(units)}
        logger.debug(f"[close_partial] trade_id={trade_id} units={units}")

        resp = self._request_with_retries("put", url, json=payload)

        if not resp.ok:
            code, msg = _extract_error_details(resp)
            log_error(
                "order_manager",
                f"Partial close failed: {code} {msg}",
                resp.text,
            )
        resp.raise_for_status()
        return resp.json()

    def close_all_positions(self) -> list:
        """Close every open position."""
        from backend.orders.position_manager import get_open_positions

        positions = get_open_positions() or []
        results = []
        for pos in positions:
            instr = pos.get("instrument")
            if not instr:
                continue
            try:
                results.append(self.close_position(instr, side="both"))
            except Exception as exc:  # pragma: no cover - network failure ignored
                logger.warning(f"close_all_positions failed for {instr}: {exc}")
        return results

    # --- Trailing‑Stop helper -------------------------------------------------
    def place_trailing_stop(
        self,
        trade_id: str,
        instrument: str,
        distance_pips: int | None = None,
    ) -> dict:
        """
        Send a TRAILING_STOP_LOSS order for the given trade.

        Args:
            trade_id (str): OANDA tradeID you want to attach the trailing stop to.
            instrument (str): e.g. “USD_JPY”.
            distance_pips (int, optional): Stop distance in pips.  If omitted,
                reads the environment variable TRAIL_DISTANCE_PIPS (default 6).

        Returns:
            dict: OANDA API JSON response.
        """
        if distance_pips is None:
            distance_pips = int(env_loader.get_env("TRAIL_DISTANCE_PIPS", 6))

        # Convert pips to price distance (JPY pairs use 0.01, most majors 0.0001)
        pip_factor = 0.01 if instrument.endswith("JPY") else 0.0001
        distance_price = distance_pips * pip_factor

        # 既存のストップロス注文を置き換える必要があるため
        # PUT /trades/{tradeID}/orders を使用する
        body = {
            "trailingStopLoss": {
                "distance": format_price(instrument, distance_price),
                "timeInForce": "GTC",
            }
        }

        url = (
            f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/" f"{trade_id}/orders"
        )

        response = self._request_with_retries("put", url, json=body)

        if response.status_code != 200:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to update trailing stop: {code} {msg}",
                response.text,
            )
            response.raise_for_status()
        return response.json()

    def attach_trailing_after_tp(
        self,
        trade_id: str,
        instrument: str,
        entry_price: float,
        atr_pips: float,
    ) -> dict | None:
        """Attach trailing stop after TP hit at breakeven.

        The trailing distance is ATR×0.3 and the stop is first moved to
        breakeven before converting to a trailing stop.
        """
        try:
            self.update_trade_sl(trade_id, instrument, entry_price)
        except Exception as exc:  # pragma: no cover - network failure ignored
            logger.warning(f"BE SL update failed: {exc}")
        distance = int(atr_pips * 0.3)
        try:
            return self.place_trailing_stop(
                trade_id=trade_id,
                instrument=instrument,
                distance_pips=distance,
            )
        except Exception as exc:  # pragma: no cover - network failure ignored
            logger.warning(f"Trailing placement failed: {exc}")
            return None

    def update_trade_sl(self, trade_id, instrument, new_sl_price):
        """Create or modify a Stop Loss order for the given trade."""
        url = (
            f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/" f"{trade_id}/orders"
        )
        body = {
            "stopLoss": {
                "price": format_price(instrument, new_sl_price),
                "timeInForce": "GTC",
            }
        }

        try:
            trade_info = fetch_trade_details(trade_id) or {}
            trade = trade_info.get("trade", {})
            if trade.get("state") != "OPEN":
                logger.debug(
                    "Trade %s not open, skipping SL update: %s",
                    trade_id,
                    trade.get("state"),
                )
                return None
        except Exception as exc:
            logger.debug(f"Failed to fetch trade details: {exc}")
            trade = {}

        min_rrr = float(env_loader.get_env("MIN_RRR", "0.8"))
        current_tp = None
        entry_price = None
        try:
            current_tp = self.get_current_tp(trade_id)
            entry_price = float(trade.get("price") or trade.get("averagePrice", 0))
        except Exception as exc:
            logger.debug(f"RRR fetch failed: {exc}")

        if current_tp is not None and entry_price is not None:
            pip = get_pip_size(instrument)
            tp_pips = abs(current_tp - entry_price) / pip
            sl_pips = abs(new_sl_price - entry_price) / pip
            if not validate_rrr(tp_pips, sl_pips, min_rrr):
                logger.warning(
                    "RRR %.2f below %.2f – rejecting SL update",
                    tp_pips / sl_pips if sl_pips else 0,
                    min_rrr,
                )
                return None

        response = self._request_with_retries("put", url, json=body)

        if response.status_code != 200:

            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to update SL: {code} {msg}",
                response.text,
            )

            return None

        result = response.json()
        log_trade(
            instrument,
            datetime.now(timezone.utc).isoformat(),
            new_sl_price,
            0,
            "SL dynamically updated",
            json.dumps(result),
            is_manual=False,
        )
        logger.debug(f"SL update response: {result}")
        return result
