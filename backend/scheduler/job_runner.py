from datetime import datetime, timedelta
import time
import uuid
import logging
from backend.utils import env_loader

from backend.market_data.tick_fetcher import fetch_tick_data

from backend.market_data.candle_fetcher import fetch_multiple_timeframes
from backend.indicators.calculate_indicators import (
    calculate_indicators,
    calculate_indicators_multi,
)


from backend.strategy.entry_logic import process_entry, _pending_limits
from backend.strategy.exit_logic import process_exit
from backend.orders.position_manager import check_current_position
from backend.orders.order_manager import OrderManager
from backend.strategy.signal_filter import pass_entry_filter
from backend.strategy.signal_filter import pass_exit_filter
from backend.strategy.openai_analysis import (
    get_market_condition,
    get_trade_plan,
    should_convert_limit_to_market,
)
from backend.strategy.higher_tf_analysis import analyze_higher_tf
from backend.strategy import pattern_scanner
import requests

from backend.utils.notification import send_line_message

#
# optional helper for pending LIMIT look‑up;
# provide stub if module is absent in current build
try:
    from backend.utils.oanda_client import get_pending_entry_order  # type: ignore
except ModuleNotFoundError:

    def get_pending_entry_order(instrument: str):
        return None


from backend.logs.update_oanda_trades import update_oanda_trades, fetch_trade_details


def build_exit_context(position, tick_data, indicators, indicators_m1=None) -> dict:
    """Compose a minimal context dict for AI exit evaluation."""
    bid = float(tick_data["prices"][0]["bids"][0]["price"])
    ask = float(tick_data["prices"][0]["asks"][0]["price"])
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    unrealized_pl_pips = float(position["unrealizedPL"]) / float(env_loader.get_env("PIP_VALUE_JPY", "100"))
    context = {
        "side": "long" if position.get("long") else "short",
        "units": abs(int(position["long"]["units"] if position.get("long") else position["short"]["units"])),
        "avg_price": float(
            position["long"]["averagePrice"] if position.get("long") else position["short"]["averagePrice"]
        ),
        "unrealized_pl_pips": unrealized_pl_pips,
        "bid": bid,
        "ask": ask,
        "spread_pips": (ask - bid) / pip_size,
        "atr_pips": indicators["atr"].iloc[-1] if hasattr(indicators["atr"], "iloc") else indicators["atr"][-1],
        "rsi": indicators["rsi"].iloc[-1] if hasattr(indicators["rsi"], "iloc") else indicators["rsi"][-1],
        "ema_slope": (
            indicators["ema_slope"].iloc[-1]
            if hasattr(indicators["ema_slope"], "iloc")
            else indicators["ema_slope"][-1]
        ),
    }
    if indicators_m1:
        context["indicators_m1"] = {
            k: (v.iloc[-1] if hasattr(v, "iloc") else v[-1])
            for k, v in indicators_m1.items()
            if isinstance(v, (list, tuple)) or hasattr(v, "iloc")
        }
    return context


log_level = env_loader.get_env("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

order_mgr = OrderManager()


DEFAULT_PAIR = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")

# Comma-separated chart pattern names used for AI analysis
PATTERN_NAMES = [
    p.strip()
    for p in env_loader.get_env(
        "PATTERN_NAMES", "double_bottom,double_top"
    ).split(",")
    if p.strip()
]

OANDA_API_KEY = env_loader.get_env("OANDA_API_KEY")
OANDA_ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
# ----- limit‑order housekeeping ------------------------------------
MAX_LIMIT_AGE_SEC = int(env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))  # seconds before a pending LIMIT is cancelled

# POSITION_REVIEW_ENABLED : "true" | "false"  – enable/disable periodic position reviews (default "true")
# POSITION_REVIEW_SEC     : seconds between AI reviews while holding a position   (default 60)
# AIに利益確定を問い合わせる閾値（TP目標の何割以上で問い合わせるか）
AI_PROFIT_TRIGGER_RATIO = float(env_loader.get_env("AI_PROFIT_TRIGGER_RATIO", "0.3"))


# ───────────────────────────────────────────────────────────
#  Check if the instrument is currently tradeable via OANDA
# ───────────────────────────────────────────────────────────
def instrument_is_tradeable(instrument: str) -> bool:
    if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
        return True  # assume open if credentials missing

    url = f"https://api-fxtrade.oanda.com/v3/accounts/{OANDA_ACCOUNT_ID}/instruments"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {"instruments": instrument}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        instruments = resp.json().get("instruments", [])
        if instruments:
            return str(instruments[0].get("tradeable", "true")).lower() == "true"
    except requests.RequestException as exc:
        logger.warning(f"instrument_is_tradeable: {exc}")
    return False


class JobRunner:
    def __init__(self, interval_seconds=1):
        self.interval_seconds = interval_seconds
        self.last_run = None
        # --- AI cooldown values ---------------------------------------
        #   * AI_COOLDOWN_SEC_OPEN : seconds between AI calls while holding a position
        #   * AI_COOLDOWN_SEC_FLAT : seconds between AI calls while flat (no position)
        self.ai_cooldown_open = int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", "30"))
        self.ai_cooldown_flat = int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", "60"))
        # Current effective cooldown (updated each loop iteration)
        self.ai_cooldown = self.ai_cooldown_flat
        # --- position review (巡回) settings ----------------------------
        self.review_enabled = env_loader.get_env("POSITION_REVIEW_ENABLED", "true").lower() == "true"
        self.review_sec = int(env_loader.get_env("POSITION_REVIEW_SEC", "60"))
        # LIMIT order age threshold
        self.max_limit_age_sec = MAX_LIMIT_AGE_SEC
        # ----- Additional runtime state --------------------------------
        # Toggle for higher‑timeframe reference levels (daily / H4)
        self.higher_tf_enabled = env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
        self.last_position_review_ts = None  # datetime of last position review
        # Epoch timestamp of last AI call (seconds)
        self.last_ai_call = datetime.min
        # Entry cooldown settings
        self.entry_cooldown_sec = int(env_loader.get_env("ENTRY_COOLDOWN_SEC", "30"))
        self.last_close_ts: datetime | None = None
        # Storage for latest indicators by timeframe
        self.indicators_M1: dict | None = None
        self.indicators_M5: dict | None = None
        self.indicators_D: dict | None = None
        # Flags for breakeven and SL management
        self.breakeven_reached: bool = False
        self.sl_reset_done: bool = False
        # Latest detected chart patterns by timeframe
        self.patterns_by_tf: dict[str, str | None] = {}

    # ────────────────────────────────────────────────────────────
    #  Poll & renew pending LIMIT orders
    # ────────────────────────────────────────────────────────────
    def _manage_pending_limits(self, instrument: str, indicators: dict, candles: list, tick_data: dict):
        """Cancel stale LIMIT orders and optionally renew them."""
        MAX_LIMIT_RETRY = int(env_loader.get_env("MAX_LIMIT_RETRY", "3"))
        pend = get_pending_entry_order(instrument)
        if not pend:
            # purge any local record if OANDA reports none
            for key, info in list(_pending_limits.items()):
                if info.get("instrument") == instrument:
                    _pending_limits.pop(key, None)
            return

        local_info = None
        for key, info in _pending_limits.items():
            if info.get("order_id") == pend.get("order_id"):
                local_info = info | {"key": key}
                break

        if local_info:
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            price = (
                float(tick_data["prices"][0]["bids"][0]["price"])
                if local_info.get("side") == "long"
                else float(tick_data["prices"][0]["asks"][0]["price"])
            )
            limit_price = float(local_info.get("limit_price", price))
            diff_pips = abs(price - limit_price) / pip_size

            atr_series = indicators.get("atr")
            if atr_series is not None and len(atr_series):
                atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
                atr_pips = float(atr_val) / pip_size
            else:
                atr_pips = 0.0

            threshold_ratio = float(env_loader.get_env("LIMIT_THRESHOLD_ATR_RATIO", "0.3"))
            adx_series = indicators.get("adx")
            adx_val = adx_series.iloc[-1] if adx_series is not None and len(adx_series) else 0.0
            if atr_pips and diff_pips >= atr_pips * threshold_ratio and adx_val >= 25:
                ctx = {
                    "diff_pips": diff_pips,
                    "atr_pips": atr_pips,
                    "adx": adx_val,
                    "side": local_info.get("side"),
                }
                try:
                    allow = should_convert_limit_to_market(ctx)
                except Exception as exc:
                    logger.warning(f"AI check failed: {exc}")
                    allow = False

                if allow:
                    try:
                        logger.info(
                            f"Switching LIMIT {pend['order_id']} to market (diff {diff_pips:.1f} pips)"
                        )
                        order_mgr.cancel_order(pend["order_id"])
                        units = int(float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")) * 1000)
                        if local_info.get("side") == "short":
                            units = -units
                        order_mgr.place_market_order(instrument, units)
                    except Exception as exc:
                        logger.warning(f"Failed to convert to market order: {exc}")
                    finally:
                        _pending_limits.pop(local_info["key"], None)
                    return

        age = time.time() - pend["ts"]
        if age < self.max_limit_age_sec:
            return

        try:
            logger.info(f"Stale LIMIT order {pend['order_id']} ({age:.0f}s) → cancelling")
            order_mgr.cancel_order(pend["order_id"])
        except Exception as exc:
            logger.warning(f"Failed to cancel LIMIT order: {exc}")
            return

        retry_count = 0
        for key, info in list(_pending_limits.items()):
            if info.get("order_id") == pend["order_id"]:
                retry_count = info.get("retry_count", 0)
                _pending_limits.pop(key, None)
        
        if retry_count >= MAX_LIMIT_RETRY:
            logger.info("LIMIT retry count exceeded – not placing new order.")
            return

        # consult AI for potential renewal
        try:
            candles_dict = {"M5": candles}
            indicators_multi = {"M5": indicators}
            plan = get_trade_plan(
                tick_data,
                indicators_multi or {},
                candles_dict or {},
                patterns=PATTERN_NAMES,
                detected_patterns=self.patterns_by_tf,
            )
        except Exception as exc:
            logger.warning(f"get_trade_plan failed: {exc}")
            return

        entry = plan.get("entry", {})
        risk = plan.get("risk", {})
        side = entry.get("side", "no").lower()
        if side not in ("long", "short") or entry.get("mode") != "limit":
            logger.info("AI does not propose renewing the LIMIT order.")
            return

        limit_price = entry.get("limit_price")
        if limit_price is None:
            logger.info("AI proposed LIMIT without price – skipping renewal.")
            return

        entry_uuid = str(uuid.uuid4())[:8]
        params = {
            "instrument": instrument,
            "side": side,
            "tp_pips": risk.get("tp_pips"),
            "sl_pips": risk.get("sl_pips"),
            "mode": "limit",
            "limit_price": limit_price,
            "entry_uuid": entry_uuid,
            "valid_for_sec": int(entry.get("valid_for_sec", self.max_limit_age_sec)),
            "risk": risk,
        }
        result = order_mgr.enter_trade(
            side=side,
            lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
            market_data=tick_data,
            strategy_params=params,
        )
        if result:
            _pending_limits[entry_uuid] = {
                "instrument": instrument,
                "order_id": result.get("order_id"),
                "ts": int(datetime.utcnow().timestamp()),
                "limit_price": limit_price,
                "side": side,
                "retry_count": retry_count + 1,
            }
            logger.info(f"Renewed LIMIT order {result.get('order_id')}")

    def run(self):
        logger.info("Job Runner started.")
        while True:
            try:
                now = datetime.utcnow()
                # ---- Market‑hours guard ---------------------------------
                if not instrument_is_tradeable(DEFAULT_PAIR):
                    logger.info(f"{DEFAULT_PAIR} market closed – sleeping 60 s")
                    time.sleep(60)
                    self.last_run = datetime.utcnow()
                    continue
                # Refresh POSITION_REVIEW_SEC dynamically each loop
                self.review_sec = int(env_loader.get_env("POSITION_REVIEW_SEC", self.review_sec))
                logger.debug(f"review_sec={self.review_sec}")
                # Refresh HIGHER_TF_ENABLED dynamically
                self.higher_tf_enabled = env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
                if self.last_run is None or (now - self.last_run) >= timedelta(seconds=self.interval_seconds):
                    logger.info(f"Running job at {now.isoformat()}")

                    # ティックデータ取得（発注用）
                    tick_data = fetch_tick_data(DEFAULT_PAIR)
                    # ティックデータ詳細はDEBUGレベルで出力
                    logger.debug(f"Tick data fetched: {tick_data}")

                    # ---- Market closed guard (price feed says non‑tradeable) ----
                    try:
                        if (not tick_data["prices"][0].get("tradeable", True)) or tick_data["prices"][0].get(
                            "status"
                        ) == "non-tradeable":
                            logger.info(f"{DEFAULT_PAIR} price feed marked non‑tradeable – sleeping 120 s")
                            time.sleep(120)
                            self.last_run = datetime.utcnow()
                            continue
                    except (IndexError, KeyError, TypeError):
                        # if structure unexpected, fall back to old check
                        pass

                    # ローソク足データ取得は一度だけ行い、後続処理で再利用する
                    candles_dict = fetch_multiple_timeframes(DEFAULT_PAIR)

                    # ---- Chart pattern detection per timeframe ----
                    self.patterns_by_tf = pattern_scanner.scan(candles_dict, PATTERN_NAMES)

                    candles_m1 = candles_dict.get("M1", [])
                    candles_m5 = candles_dict.get("M5", [])
                    candles_d1 = candles_dict.get("D", [])
                    candles = candles_m5  # backward compatibility
                    logger.info(
                        f"Candle M5 last: {candles_m5[-1] if candles_m5 else 'No candles'}"
                    )

                    # -------- Higher‑timeframe reference levels --------
                    higher_tf = {}
                    if self.higher_tf_enabled:
                        higher_tf = analyze_higher_tf(DEFAULT_PAIR)
                        logger.debug(f"Higher‑TF levels: {higher_tf}")

                    # 指標計算
                    indicators_multi = calculate_indicators_multi(candles_dict)
                    self.indicators_M1 = indicators_multi.get("M1")
                    self.indicators_M5 = indicators_multi.get("M5")
                    self.indicators_D = indicators_multi.get("D")
                    indicators = self.indicators_M5

                    logger.info("Indicators calculation successful.")

                    # チェック：保留LIMIT注文の更新
                    self._manage_pending_limits(DEFAULT_PAIR, indicators, candles_m5, tick_data)

                    # ポジション確認
                    has_position = check_current_position(DEFAULT_PAIR)
                    logger.info(f"Current position status: {has_position}")
                    logger.info(f"Has open position for {DEFAULT_PAIR}: {has_position}")

                    if not has_position:
                        self.breakeven_reached = False
                        self.sl_reset_done = False

                    # ---- Dynamic cooldown (OPEN / FLAT) ---------------
                    if has_position:
                        self.ai_cooldown = self.ai_cooldown_open
                    else:
                        self.ai_cooldown = self.ai_cooldown_flat

                    # Determine position_side for further logic
                    if has_position and has_position.get("long") and int(has_position["long"]["units"]) > 0:
                        position_side = "long"
                    elif has_position and has_position.get("short") and int(has_position["short"]["units"]) < 0:
                        position_side = "short"
                    else:
                        position_side = None

                    # Inserted logic for dynamic SL management and AI profit-taking consultation
                    if has_position and position_side:
                        current_price = (
                            float(tick_data["prices"][0]["bids"][0]["price"])
                            if position_side == "long"
                            else float(tick_data["prices"][0]["asks"][0]["price"])
                        )
                        entry_price = float(has_position[position_side]["averagePrice"])

                        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                        current_profit_pips = (
                            (current_price - entry_price) / pip_size
                            if position_side == "long"
                            else (entry_price - current_price) / pip_size
                        )

                        BE_TRIGGER_PIPS = float(env_loader.get_env("BE_TRIGGER_PIPS", "10"))
                        TP_PIPS = float(env_loader.get_env("INIT_TP_PIPS", "30"))
                        AI_PROFIT_TRIGGER_RATIO = float(env_loader.get_env("AI_PROFIT_TRIGGER_RATIO", "0.3"))

                        logger.info(
                            f"profit_pips={current_profit_pips:.1f}, "
                            f"BE_trigger={BE_TRIGGER_PIPS}, "
                            f"AI_trigger={TP_PIPS * AI_PROFIT_TRIGGER_RATIO}"
                        )

                        if current_profit_pips >= BE_TRIGGER_PIPS and not self.breakeven_reached:
                            new_sl_price = entry_price
                            trade_id = has_position[position_side]["tradeIDs"][0]
                            result = order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                            if result is None:
                                logger.warning("SL update failed on first attempt; retrying")
                                result = order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                                if result is None:
                                    logger.error("SL update failed after retry")
                            if result is not None:
                                logger.info(
                                    f"SL updated to entry price to secure minimum profit: {new_sl_price}"
                                )
                                self.breakeven_reached = True
                                self.sl_reset_done = False

                        if self.breakeven_reached and not self.sl_reset_done:
                            trade_id = has_position[position_side]["tradeIDs"][0]
                            sl_missing = True
                            try:
                                trade_info = fetch_trade_details(trade_id) or {}
                                trade = trade_info.get("trade", {})
                                sl_price = float(trade.get("stopLossOrder", {}).get("price", 0))
                                sl_missing = sl_price == 0
                            except Exception as exc:
                                logger.warning(f"Failed to fetch trade details: {exc}")
                            if sl_missing:
                                atr_val = indicators["atr"].iloc[-1] if hasattr(indicators["atr"], "iloc") else indicators["atr"][-1]
                                if position_side == "long":
                                    new_sl_price = entry_price - atr_val * 2
                                else:
                                    new_sl_price = entry_price + atr_val * 2
                                result = order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                                if result is None:
                                    logger.warning("SL reapply failed on first attempt; retrying")
                                    result = order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                                if result is not None:
                                    logger.info(f"SL reapplied at {new_sl_price}")
                                    self.sl_reset_done = True

                        if current_profit_pips >= TP_PIPS * AI_PROFIT_TRIGGER_RATIO:
                            # EXITフィルターを評価し、フィルターNGの場合はAIの決済判断をスキップ
                            if pass_exit_filter(indicators, position_side):
                                logger.info("Filter OK → Processing exit decision with AI.")
                                self.last_ai_call = datetime.now()
                                market_cond = get_market_condition(
                                    {
                                        "indicators": {
                                            key: float(val.iloc[-1]) if hasattr(val, "iloc") else float(val)
                                            for key, val in indicators.items()
                                        },
                                        "candles_m1": candles_m1,
                                        "candles_m5": candles_m5,
                                        "candles_d1": candles_d1,
                                    }
                                )
                                logger.debug(f"Market condition (exit): {market_cond}")
                                exit_executed = process_exit(
                                    indicators,
                                    tick_data,
                                    market_cond,
                                    higher_tf,
                                    indicators_m1=self.indicators_M1,
                                    patterns=PATTERN_NAMES,
                                    pattern_names=self.patterns_by_tf,
                                )
                                if exit_executed:
                                    self.last_close_ts = datetime.utcnow()
                                    logger.info("Position closed based on AI recommendation.")
                                    send_line_message(
                                        f"【EXIT】{DEFAULT_PAIR} {current_price} で決済しました。PL={current_profit_pips:.1f}pips"
                                    )
                                else:
                                    logger.info("AI decision was HOLD → No exit executed.")
                            else:
                                logger.info("Filter NG → AI exit decision skipped.")

                    # ---- Position‑review timing -----------------------------
                    due_for_review = False
                    if has_position and self.review_enabled:
                        if self.last_position_review_ts is None:
                            due_for_review = True
                        else:
                            elapsed_review = (now - self.last_position_review_ts).total_seconds()
                            due_for_review = elapsed_review >= self.review_sec

                    # --- Cool‑down check ------------------------------------
                    elapsed_seconds = (datetime.now() - self.last_ai_call).total_seconds()
                    if (not due_for_review) and elapsed_seconds < self.ai_cooldown:
                        logger.info(
                            f"AI cooldown active ({elapsed_seconds:.1f}s < {self.ai_cooldown}s). Skipping AI call."
                        )
                        self.last_run = now
                        # Update OANDA trade history every second
                        update_oanda_trades()
                        time.sleep(self.interval_seconds)
                        continue

                    # Periodic exit review
                    if has_position and due_for_review:
                        self.last_position_review_ts = now
                        if position_side:
                            cur_price = (
                                float(tick_data["prices"][0]["bids"][0]["price"])
                                if position_side == "long"
                                else float(tick_data["prices"][0]["asks"][0]["price"])
                            )
                            entry_price = float(has_position[position_side]["averagePrice"])
                            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                            profit_pips = (
                                (cur_price - entry_price) / pip_size
                                if position_side == "long"
                                else (entry_price - cur_price) / pip_size
                            )
                        else:
                            cur_price = float(tick_data["prices"][0]["bids"][0]["price"])
                            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                            profit_pips = 0.0

                        if pass_exit_filter(indicators, position_side):
                            logger.info("Filter OK → Processing periodic exit decision with AI.")
                            self.last_ai_call = datetime.now()
                            market_cond = get_market_condition(
                                {
                                    "indicators": {
                                        key: float(val.iloc[-1]) if hasattr(val, "iloc") else float(val)
                                        for key, val in indicators.items()
                                    },
                                    "candles_m1": candles_m1,
                                    "candles_m5": candles_m5,
                                    "candles_d1": candles_d1,
                                }
                            )
                            logger.debug(f"Market condition (review): {market_cond}")
                            exit_executed = process_exit(
                                indicators,
                                tick_data,
                                market_cond,
                                higher_tf,
                                indicators_m1=self.indicators_M1,
                                patterns=PATTERN_NAMES,
                                pattern_names=self.patterns_by_tf,
                            )
                            if exit_executed:
                                self.last_close_ts = datetime.utcnow()
                                logger.info("Position closed based on AI recommendation.")
                                send_line_message(
                                    f"【EXIT】{DEFAULT_PAIR} {cur_price} で決済しました。PL={profit_pips * pip_size:.2f}"
                                )
                            else:
                                logger.info("AI decision was HOLD → No exit executed.")
                        else:
                            logger.info("Filter NG → AI exit decision skipped.")

                    # AIによるエントリー/エグジット判断
                    if not has_position:
                        # 1) Entry cooldown check
                        if (
                            self.last_close_ts
                            and (datetime.utcnow() - self.last_close_ts).total_seconds() < self.entry_cooldown_sec
                        ):
                            logger.info(
                                f"Entry cooldown active ({(datetime.utcnow() - self.last_close_ts).total_seconds():.1f}s < {self.entry_cooldown_sec}s). Skipping entry."
                            )
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            continue

                        # 2) Pivot-based suppression: avoid entries near specified pivots
                        if self.higher_tf_enabled:
                            current_price = float(tick_data["prices"][0]["bids"][0]["price"])
                            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                            sup_pips = float(env_loader.get_env("PIVOT_SUPPRESSION_PIPS", "15"))
                            tfs = [
                                tf.strip().upper()
                                for tf in env_loader.get_env("PIVOT_SUPPRESSION_TFS", "D").split(",")
                                if tf.strip()
                            ]
                            suppress = False
                            for tf in tfs:
                                pivot = higher_tf.get(f"pivot_{tf.lower()}")
                                if pivot is None:
                                    continue
                                if abs((current_price - pivot) / pip_size) <= sup_pips:
                                    logger.info(
                                        f"Pivot suppression: price {current_price} within {sup_pips} pips of {tf} pivot {pivot}. Skipping entry."
                                    )
                                    suppress = True
                                    break
                            if suppress:
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                continue

                        # ── Entry side ───────────────────────────────
                        current_price = float(tick_data["prices"][0]["bids"][0]["price"])
                        if pass_entry_filter(indicators, current_price, self.indicators_M1):
                            logger.info("Filter OK → Processing entry decision with AI.")
                            self.last_ai_call = datetime.now()  # record AI call time *before* the call
                            market_cond = get_market_condition(
                                {
                                    "indicators": {
                                        key: float(val.iloc[-1]) if hasattr(val, "iloc") else float(val)
                                        for key, val in indicators.items()
                                    },
                                    "candles_m1": candles_m1,
                                    "candles_m5": candles_m5,
                                    "candles_d1": candles_d1,
                                }
                            )
                            logger.debug(f"Market condition (post‑filter): {market_cond}")
                            result = process_entry(
                                indicators,
                                candles_m5,
                                tick_data,
                                market_cond,
                                higher_tf=higher_tf,
                                patterns=PATTERN_NAMES,
                                pattern_names=self.patterns_by_tf,
                            )
                            if not result:
                                logger.info("process_entry returned False → aborting entry and continuing loop")
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                continue
                            # Send LINE notification on entry
                            price = float(tick_data["prices"][0]["bids"][0]["price"])
                            send_line_message(f"【ENTRY】{DEFAULT_PAIR} {price} でエントリーしました。")
                        else:
                            logger.info("Filter NG → AI entry decision skipped.")
                            self.last_position_review_ts = None
                    # (removed: periodic exit check block)
                # Update OANDA trade history every second
                self.last_run = now

                update_oanda_trades()
                time.sleep(self.interval_seconds)

            except Exception as e:
                logger.error(f"Error occurred during job execution: {e}", exc_info=True)
                time.sleep(self.interval_seconds)


if __name__ == "__main__":
    runner = JobRunner(interval_seconds=1)
    runner.run()
