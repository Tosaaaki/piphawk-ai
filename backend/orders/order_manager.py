import os
import requests
from backend.logs.log_manager import log_trade, log_error
from backend.utils.price import format_price
from datetime import datetime, timedelta
import time
import json
import logging
import uuid
logger = logging.getLogger(__name__)

OANDA_API_URL = os.getenv("OANDA_API_URL", "https://api-fxtrade.oanda.com/v3")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
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
DEFAULT_PAIR = os.getenv("DEFAULT_PAIR", "USD_JPY")

PIP_SIZES: dict[str, float] = {
    "USD_JPY": 0.01,
    "EUR_USD": 0.0001,
    # add more pairs here if necessary
}

def get_pip_size(instrument: str) -> float:
    """Return pip size for the instrument; fallback to DEFAULT_PAIR mapping."""
    return PIP_SIZES.get(instrument, PIP_SIZES.get(DEFAULT_PAIR, 0.01))


class OrderManager:

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

        comment_dict = {"entry_uuid": entry_uuid, "mode": "limit"}
        if risk_info:
            comment_dict.update(tp=risk_info.get("tp_pips"),
                                sl=risk_info.get("sl_pips"),
                                pp=risk_info.get("tp_prob"),
                                qp=risk_info.get("sl_prob"))
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
                "clientExtensions": {
                    "comment": comment_json,
                    "tag": tag
                },
                "gtdTime": (datetime.utcnow() + 
                            timedelta(seconds=valid_sec)).isoformat("T") + "Z"
            }
        }
        if tp_price and sl_price:
            payload["order"]["takeProfitOnFill"] = {
                "price": format_price(instrument, tp_price)
            }
            payload["order"]["stopLossOnFill"] = {
                "price": format_price(instrument, sl_price)
            }

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        r = requests.post(url, json=payload, headers=HEADERS)
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
        r = requests.put(url, headers=HEADERS)
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
                "gtdTime": (datetime.utcnow() +
                            timedelta(seconds=valid_sec)).isoformat("T") + "Z"
            }
        }
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders/{order_id}"
        r = requests.put(url, json=payload, headers=HEADERS)
        if not r.ok:
            code, msg = _extract_error_details(r)
            log_error(
                "order_manager",
                f"Modify order price failed: {code} {msg}",
                r.text,
            )
            r.raise_for_status()
        return r.json()

    def place_market_order(self, instrument, units):
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        response = requests.post(url, json=data, headers=HEADERS)
        logger.debug(
            f"Market order response: {response.status_code} {response.text}"
        )
        if response.status_code != 201:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to place order: {code} {msg}",
                response.text,
            )
            raise Exception(f"Failed to place order: {response.text}")
        return response.json()

    def adjust_tp_sl(self, instrument, trade_id, new_tp=None, new_sl=None):
        """Adjust TP and/or SL using individual STOP_LOSS/TAKE_PROFIT orders."""
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

        if new_tp is not None:
            for attempt in range(3):
                response = requests.put(url, json=tp_payload, headers=HEADERS)
                if response.status_code == 200:
                    results["tp"] = response.json()
                    break

                code, msg = _extract_error_details(response)
                err_msg = f"TP adjustment failed: {code} {msg}"

                if code in ("NO_SUCH_TRADE", "ORDER_DOESNT_EXIST") or (
                    "NO_SUCH_TRADE" in response.text or "ORDER_DOESNT_EXIST" in response.text
                ):
                    log_error("order_manager", err_msg, response.text)
                    break

                if attempt == 2:
                    log_error("order_manager", err_msg, response.text)
                time.sleep(1)

        if new_sl is not None:
            sl_payload = {
                "order": {
                    "type": "STOP_LOSS",
                    "tradeID": trade_id,
                    "price": format_price(instrument, new_sl),
                    "timeInForce": "GTC",
                }
            }
            for attempt in range(3):
                resp = requests.post(url, json=sl_payload, headers=HEADERS)
                if resp.status_code == 201:
                    results["sl"] = resp.json()
                    break
                if attempt == 2:
                    code, msg = _extract_error_details(resp)
                    log_error(
                        "order_manager",
                        f"SL adjustment failed: {code} {msg}",
                        resp.text,
                    )
                time.sleep(1)

        return results if results else None

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
    ):
        min_lot = float(os.getenv("MIN_TRADE_LOT", "0.01"))
        max_lot = float(os.getenv("MAX_TRADE_LOT", "0.1"))
        lot_size = max(min_lot, min(lot_size, max_lot))

        mode = strategy_params.get("mode", "market")
        limit_price = strategy_params.get("limit_price")
        if force_limit_only and mode == "market" and limit_price is not None:
            logger.debug(
                "[enter_trade] force_limit_only=True → converting market to limit"
            )
            mode = "limit"
        entry_uuid = strategy_params.get("entry_uuid") or str(uuid.uuid4())[:8]
        valid_sec = int(strategy_params.get("valid_for_sec", os.getenv("MAX_LIMIT_AGE_SEC", "180")))

        instrument = strategy_params["instrument"]
        tp_pips = strategy_params.get("tp_pips")
        sl_pips = strategy_params.get("sl_pips")
        pip = get_pip_size(instrument)
        # side = strategy_params.get("side", "long").lower()

        entry_price = float(market_data['prices'][0]['bids'][0]['price']) if side == "long" else float(market_data['prices'][0]['asks'][0]['price'])
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_time = datetime.utcnow().isoformat()

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
                risk_info=strategy_params.get("risk")
            )

        # ---- embed entry‑regime JSON into clientExtensions.comment (≤255 bytes) ----
        comment_json = None
        try:
            regime_info = strategy_params.get("market_cond", {}) or {}
            comment_dict = {
                "regime": regime_info.get("market_condition"),
                "dir": regime_info.get("trend_direction"),
                "mode": mode,
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
                comment_json = comment_json.encode("utf-8")[:240].decode("utf-8", "ignore")
        except Exception as exc:
            logger.debug(f"[enter_trade] building comment JSON failed: {exc}")

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        order_body = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        if comment_json:
            order_body["order"]["clientExtensions"] = {"comment": comment_json}

        if tp_pips and sl_pips:
            if side == "long":
                tp_price = entry_price + float(tp_pips) * pip
                sl_price = entry_price - float(sl_pips) * pip
            else:
                tp_price = entry_price - float(tp_pips) * pip
                sl_price = entry_price + float(sl_pips) * pip

            order_body["order"]["takeProfitOnFill"] = {
                "price": format_price(instrument, tp_price)
            }
            order_body["order"]["stopLossOnFill"] = {
                "price": format_price(instrument, sl_price)
            }

        response = requests.post(url, json=order_body, headers=HEADERS)
        logger.debug(f"Order placement response: {response.status_code} - {response.text}")
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
            entry_regime=entry_regime
        )
        return result

    def exit_trade(self, position):
        instrument = position["instrument"]
        units_val = float(position.get("units", 0))
        # log raw position info before side detection
        logger.debug(f"[exit_trade] raw units={units_val} position={position}")

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to fetch position details: {code} {msg}",
                response.text,
            )
            raise Exception(f"Failed to fetch position details: {response.text}")

        position_data = response.json()['position']
        long_units = int(position_data['long']['units'])
        short_units = int(position_data['short']['units'])

        if short_units < 0:
            side = "short"
        elif long_units > 0:
            side = "long"
        else:
            side = "both"

        logger.debug(f"[exit_trade] API-based detected side={side} for {instrument}")
        result = self.close_position(instrument, side)

        entry_price = float(position['long']['averagePrice'] if int(position['long']['units']) > 0 else position['short']['averagePrice'])

        if side == "long":
            units = int(position['long']['units'])
        elif side == "short":
            units = int(position['short']['units'])
        else:
            units = 0

        log_trade(
            instrument=instrument,
            entry_time=position.get('entry_time', datetime.utcnow().isoformat()),
            entry_price=entry_price,
            units=units,
            ai_reason="exit",
            exit_time=datetime.utcnow().isoformat()
        )
        return result

    def close_position(self, instrument, side: str = "both"):
        if side is None:
            raise ValueError("side must be 'long', 'short', or 'both'")
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}/close"

        # OANDA spec: we must explicitly specify which side(s) to close
        if side == "short":
            payload = {"shortUnits": "ALL"}
        elif side == "long":
            payload = {"longUnits": "ALL"}
        else:
            # close both sides explicitly
            payload = {"longUnits": "ALL", "shortUnits": "ALL"}

        logger.debug(f"[close_position] payload={payload}")
        response = requests.put(url, json=payload, headers=HEADERS)

        if not response.ok:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to close position: {code} {msg}",
                response.text,
            )
            raise Exception(f"Failed to close position: {response.text}")

        return response.json()

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
            distance_pips = int(os.getenv("TRAIL_DISTANCE_PIPS", 6))

        # Convert pips to price distance (JPY pairs use 0.01, most majors 0.0001)
        pip_factor = 0.01 if instrument.endswith("JPY") else 0.0001
        distance_price = distance_pips * pip_factor

        order_spec = {
            "order": {
                "type": "TRAILING_STOP_LOSS",
                "tradeID": trade_id,
                "distance": format_price(instrument, distance_price),
                "timeInForce": "GTC",
            }
        }

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        response = requests.post(url, json=order_spec, headers=HEADERS)
        if not response.ok:
            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to place trailing stop: {code} {msg}",
                response.text,
            )
            response.raise_for_status()
        return response.json()

    def update_trade_sl(self, trade_id, instrument, new_sl_price):
        """Create or modify a Stop Loss order for the given trade."""
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        body = {
            "order": {
                "type": "STOP_LOSS",

                "tradeID": trade_id,
                "price": format_price(instrument, new_sl_price),
                "timeInForce": "GTC",
            }
        }

        response = requests.post(url, json=body, headers=HEADERS)

        if response.status_code != 200:

            code, msg = _extract_error_details(response)
            log_error(
                "order_manager",
                f"Failed to update SL: {code} {msg}",
                response.text,
            )

            return None

        log_trade(
            instrument,
            datetime.utcnow().isoformat(),
            new_sl_price,
            0,
            "SL dynamically updated",
            "SL_UPDATE",
        )
        return response.json()
