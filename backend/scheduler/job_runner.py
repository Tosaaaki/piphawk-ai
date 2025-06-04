from datetime import datetime, timedelta
import time
import uuid
import logging
import json
import os
from backend.utils import env_loader

from backend.market_data.tick_fetcher import fetch_tick_data

from backend.market_data.candle_fetcher import fetch_multiple_timeframes
from backend.indicators.calculate_indicators import (
    calculate_indicators,
    calculate_indicators_multi,
)


from backend.strategy.entry_logic import process_entry, _pending_limits
from backend.strategy.exit_logic import process_exit
from backend.strategy.exit_ai_decision import evaluate as evaluate_exit_ai
try:
    from backend.orders.position_manager import (
        check_current_position,
        get_margin_used,
        get_position_details,
    )
except ImportError:  # tests may stub position_manager without helpers
    from backend.orders.position_manager import check_current_position

    def get_margin_used(*_args, **_kwargs):
        return None

    def get_position_details(*_args, **_kwargs):
        return None
from backend.orders.order_manager import OrderManager
try:
from backend.strategy.signal_filter import (
        pass_entry_filter,
        filter_pre_ai,
        detect_climax_reversal,
        counter_trend_block,
        consecutive_lower_lows,
    )
except Exception:  # pragma: no cover - test stubs may lack filter_pre_ai
    from backend.strategy.signal_filter import pass_entry_filter

    def filter_pre_ai(*_args, **_kwargs):
        return False
    def detect_climax_reversal(*_a, **_k):
        return None
    def counter_trend_block(*_a, **_k):
        return False
from analysis.signal_filter import is_multi_tf_aligned
from backend.logs.perf_stats_logger import PerfTimer
from backend.strategy.signal_filter import pass_exit_filter
from backend.strategy.openai_analysis import (
    get_market_condition,
    get_trade_plan,
    should_convert_limit_to_market,
)
from backend.strategy.higher_tf_analysis import analyze_higher_tf
from backend.strategy import pattern_scanner
from backend.strategy.momentum_follow import follow_breakout
import requests

from backend.utils.notification import send_line_message
from backend.logs.trade_logger import log_trade, ExitReason

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
    side = "long" if int(position.get("long", {}).get("units", 0)) != 0 else "short"
    context = {
        "side": side,
        "units": abs(int(position[side].get("units", 0))),
        "avg_price": float(position[side].get("averagePrice", 0.0)),
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
    p.strip() for p in env_loader.get_env("PATTERN_NAMES", "double_bottom,double_top").split(",") if p.strip()
]

OANDA_API_KEY = env_loader.get_env("OANDA_API_KEY")
OANDA_ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
MARGIN_WARNING_THRESHOLD = float(env_loader.get_env("MARGIN_WARNING_THRESHOLD", "0"))
# Additional lot size for scaling into an existing position
SCALE_LOT_SIZE = float(env_loader.get_env("SCALE_LOT_SIZE", "0.5"))
# ----- limit‑order housekeeping ------------------------------------
MAX_LIMIT_AGE_SEC = int(env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))  # seconds before a pending LIMIT is cancelled
PENDING_GRACE_MIN = int(env_loader.get_env("PENDING_GRACE_MIN", "3"))
SL_COOLDOWN_SEC = int(env_loader.get_env("SL_COOLDOWN_SEC", "300"))

# POSITION_REVIEW_ENABLED : "true" | "false"  – enable/disable periodic position reviews (default "true")
# POSITION_REVIEW_SEC     : seconds between AI reviews while holding a position   (default 60)
# AIに利益確定を問い合わせる閾値（TP目標の何割以上で問い合わせるか）
AI_PROFIT_TRIGGER_RATIO = float(env_loader.get_env("AI_PROFIT_TRIGGER_RATIO", "0.3"))
TP_EXTENSION_ENABLED = env_loader.get_env("TP_EXTENSION_ENABLED", "false").lower() == "true"
TP_EXTENSION_ADX_MIN = float(env_loader.get_env("TP_EXTENSION_ADX_MIN", "25"))
TP_EXTENSION_ATR_MULT = float(env_loader.get_env("TP_EXTENSION_ATR_MULT", "1.0"))
TP_REDUCTION_ENABLED = env_loader.get_env("TP_REDUCTION_ENABLED", "false").lower() == "true"
TP_REDUCTION_ADX_MAX = float(env_loader.get_env("TP_REDUCTION_ADX_MAX", "20"))
TP_REDUCTION_MIN_SEC = int(env_loader.get_env("TP_REDUCTION_MIN_SEC", "900"))
TP_REDUCTION_ATR_MULT = float(env_loader.get_env("TP_REDUCTION_ATR_MULT", "1.0"))

# Peak profit exit settings
PEAK_EXIT_ENABLED = env_loader.get_env("PEAK_EXIT_ENABLED", "false").lower() == "true"
PEAK_EXIT_RETRACE_PIPS = float(env_loader.get_env("PEAK_EXIT_RETRACE_PIPS", "2"))


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
        #   * AI_COOLDOWN_SEC_OPEN : エントリー用クールダウン時間
        #   * AI_COOLDOWN_SEC_FLAT : エグジット用クールダウン時間
        self.ai_cooldown_open = int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", "30"))
        self.ai_cooldown_flat = int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", "60"))
        # 現在のクールダウン（ループ毎に更新）
        self.ai_cooldown = self.ai_cooldown_open
        # --- position review (巡回) settings ----------------------------
        self.review_enabled = env_loader.get_env("POSITION_REVIEW_ENABLED", "true").lower() == "true"
        self.review_sec = int(env_loader.get_env("POSITION_REVIEW_SEC", "60"))
        # LIMIT order age threshold
        self.max_limit_age_sec = MAX_LIMIT_AGE_SEC
        self.pending_grace_sec = PENDING_GRACE_MIN * 60
        # ----- Additional runtime state --------------------------------
        # Toggle for higher‑timeframe reference levels (daily / H4)
        self.higher_tf_enabled = env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
        self.last_position_review_ts = None  # datetime of last position review
        # Epoch timestamp of last AI call (seconds)
        self.last_ai_call = datetime.min
        # Entry cooldown settings
        self.entry_cooldown_sec = int(env_loader.get_env("ENTRY_COOLDOWN_SEC", "30"))
        self.last_close_ts: datetime | None = None
        # --- last stop-loss info ----------------------------------
        self.last_sl_side: str | None = None
        self.last_sl_time: datetime | None = None
        self.sl_cooldown_sec = SL_COOLDOWN_SEC
        # Storage for latest indicators by timeframe
        self.indicators_M1: dict | None = None
        self.indicators_M5: dict | None = None
        self.indicators_M15: dict | None = None
        self.indicators_H1: dict | None = None
        self.indicators_H4: dict | None = None
        self.indicators_D: dict | None = None
        # Flags for breakeven and SL management
        self.breakeven_reached: bool = False
        self.sl_reset_done: bool = False
        self.tp_extended: bool = False
        self.tp_reduced: bool = False
        # Latest detected chart patterns by timeframe
        self.patterns_by_tf: dict[str, str | None] = {}
        # Highest profit observed since entry
        self.max_profit_pips: float = 0.0
        # recent M5 candles for peak detection
        self.last_candles_m5: list[dict] | None = None

        # Restore TP adjustment flags based on existing TP order comment
        try:
            pos = get_position_details(DEFAULT_PAIR)
            if pos:
                er_raw = pos.get("entry_regime")
                tp_comment = pos.get("tp_comment")
                if er_raw and tp_comment:
                    er = json.loads(er_raw)
                    entry_uuid = er.get("entry_uuid")
                    if entry_uuid and entry_uuid in tp_comment:
                        self.tp_extended = True
                        self.tp_reduced = True
        except Exception as exc:  # pragma: no cover - ignore init failures
            logger.debug(f"TP flag restore failed: {exc}")

        token = os.getenv("LINE_CHANNEL_TOKEN", "")
        user_id = os.getenv("LINE_USER_ID", "")
        logger.info(
            "JobRunner startup - LINE token set: %s, user ID set: %s",
            bool(token),
            bool(user_id),
        )

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

            # --- gather additional indicators for AI decision -----------------
            rsi_series = indicators.get("rsi")
            rsi_val = rsi_series.iloc[-1] if rsi_series is not None and len(rsi_series) else None

            ema_slope_series = indicators.get("ema_slope")
            ema_slope_val = (
                ema_slope_series.iloc[-1]
                if ema_slope_series is not None and len(ema_slope_series)
                else None
            )

            bb_upper = indicators.get("bb_upper")
            bb_lower = indicators.get("bb_lower")
            bb_width_pips = None
            if (
                bb_upper is not None
                and bb_lower is not None
                and len(bb_upper)
                and len(bb_lower)
            ):
                bb_width_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size

            if atr_pips and diff_pips >= atr_pips * threshold_ratio and adx_val >= 25:
                ctx = {
                    "diff_pips": diff_pips,
                    "atr_pips": atr_pips,
                    "adx": adx_val,
                    "rsi": rsi_val,
                    "ema_slope": ema_slope_val,
                    "bb_width_pips": bb_width_pips,
                    "side": local_info.get("side"),
                }
                try:
                    allow = should_convert_limit_to_market(ctx)
                except Exception as exc:
                    logger.warning(f"AI check failed: {exc}")
                    allow = False

                if allow:
                    try:
                        logger.info(f"Switching LIMIT {pend['order_id']} to market (diff {diff_pips:.1f} pips)")
                        order_mgr.cancel_order(pend["order_id"])
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
                            risk = plan.get("risk", {})
                            ai_raw = json.dumps(plan, ensure_ascii=False)
                        except Exception as exc:
                            logger.warning(f"get_trade_plan failed: {exc}")
                            risk = {}
                            ai_raw = None

                        try:
                            ctx = {
                                "indicators": {
                                    k: float(val.iloc[-1]) if hasattr(val, "iloc") and val.iloc[-1] is not None
                                    else float(val) if val is not None else None
                                    for k, val in indicators.items()
                                },
                                "indicators_h1": {
                                    k: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                    else float(v) if v is not None else None
                                    for k, v in (self.indicators_H1 or {}).items()
                                },
                                "indicators_h4": {
                                    k: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                    else float(v) if v is not None else None
                                    for k, v in (self.indicators_H4 or {}).items()
                                },
                            }
                            market_cond = get_market_condition(ctx, {})
                        except Exception as exc:
                            logger.warning(f"get_market_condition failed: {exc}")
                            market_cond = None

                        params = {
                            "instrument": instrument,
                            "side": local_info.get("side"),
                            "tp_pips": risk.get("tp_pips"),
                            "sl_pips": risk.get("sl_pips"),
                            "mode": "market",
                            "limit_price": None,
                            "market_cond": market_cond,
                            "ai_response": ai_raw,
                        }
                        result = order_mgr.enter_trade(
                            side=local_info.get("side"),
                            lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
                            market_data=tick_data,
                            strategy_params=params,
                        )
                    except Exception as exc:
                        logger.warning(f"Failed to convert to market order: {exc}")
                    else:
                        if result:
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

    def _maybe_extend_tp(self, position: dict, indicators: dict, side: str, pip_size: float):
        if self.tp_extended or not TP_EXTENSION_ENABLED:
            return
        adx_series = indicators.get("adx")
        atr_series = indicators.get("atr")
        if adx_series is None or atr_series is None:
            return
        adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
        if adx_val < TP_EXTENSION_ADX_MIN:
            return
        atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
        ext_pips = (atr_val / pip_size) * TP_EXTENSION_ATR_MULT
        try:
            entry_price = float(position[side].get("averagePrice", 0.0))
            trade_id = position[side]["tradeIDs"][0]
            er_raw = position.get("entry_regime")
            entry_uuid = None
            if er_raw:
                try:
                    entry_uuid = json.loads(er_raw).get("entry_uuid")
                except Exception:
                    entry_uuid = None
        except Exception:
            return
        new_tp = entry_price + ext_pips * pip_size if side == "long" else entry_price - ext_pips * pip_size
        current_tp = None
        if hasattr(order_mgr, "get_current_tp"):
            current_tp = order_mgr.get_current_tp(trade_id)
        if current_tp is not None and abs(current_tp - new_tp) < pip_size * 0.1:
            return
        try:
            res = order_mgr.adjust_tp_sl(
                DEFAULT_PAIR,
                trade_id,
                new_tp=new_tp,
                entry_uuid=entry_uuid,
            )
            if res is not None:
                logger.info(
                    f"TP extended from {current_tp} to {new_tp} ({ext_pips:.1f}pips) due to strong trend"
                )
                self.tp_extended = True
        except Exception as exc:
            logger.warning(f"TP extension failed: {exc}")

    def _maybe_reduce_tp(self, position: dict, indicators: dict, side: str, pip_size: float):
        if self.tp_reduced or not TP_REDUCTION_ENABLED:
            return
        adx_series = indicators.get("adx")
        atr_series = indicators.get("atr")
        if adx_series is None or atr_series is None:
            return
        adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
        if adx_val > TP_REDUCTION_ADX_MAX:
            return
        entry_ts = position.get("entry_time") or position.get("openTime")
        if entry_ts:
            try:
                et = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                held_sec = (datetime.utcnow() - et).total_seconds()
                if held_sec < TP_REDUCTION_MIN_SEC:
                    return
            except Exception:
                pass
        atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
        red_pips = (atr_val / pip_size) * TP_REDUCTION_ATR_MULT
        try:
            entry_price = float(position[side].get("averagePrice", 0.0))
            trade_id = position[side]["tradeIDs"][0]
            er_raw = position.get("entry_regime")
            entry_uuid = None
            if er_raw:
                try:
                    entry_uuid = json.loads(er_raw).get("entry_uuid")
                except Exception:
                    entry_uuid = None
        except Exception:
            return
        new_tp = entry_price + red_pips * pip_size if side == "long" else entry_price - red_pips * pip_size
        current_tp = None
        if hasattr(order_mgr, "get_current_tp"):
            current_tp = order_mgr.get_current_tp(trade_id)
        if current_tp is not None and abs(current_tp - new_tp) < pip_size * 0.1:
            return
        try:
            res = order_mgr.adjust_tp_sl(
                DEFAULT_PAIR,
                trade_id,
                new_tp=new_tp,
                entry_uuid=entry_uuid,
            )
            if res is not None:
                logger.info(
                    f"TP reduced from {current_tp} to {new_tp} ({red_pips:.1f}pips) due to weak trend"
                )
                self.tp_reduced = True
        except Exception as exc:
            logger.warning(f"TP reduction failed: {exc}")

    # ────────────────────────────────────────────────────────────
    #  Trailing-stop settings update based on calendar/quiet hours
    # ────────────────────────────────────────────────────────────
    def get_calendar_volatility_level(self) -> int:
        try:
            return int(env_loader.get_env("CALENDAR_VOLATILITY_LEVEL", "0"))
        except (TypeError, ValueError):
            return 0

    def _refresh_trailing_status(self) -> None:
        """Update trailing-stop enable flag based on time or event level."""
        from backend.strategy import exit_logic
        quiet_start = float(env_loader.get_env("QUIET_START_HOUR_JST", "3"))
        quiet_end = float(env_loader.get_env("QUIET_END_HOUR_JST", "7"))
        quiet2_enabled = env_loader.get_env("QUIET2_ENABLED", "false").lower() == "true"
        if quiet2_enabled:
            quiet2_start = float(env_loader.get_env("QUIET2_START_HOUR_JST", "23"))
            quiet2_end = float(env_loader.get_env("QUIET2_END_HOUR_JST", "1"))
        else:
            quiet2_start = quiet2_end = None

        now_jst = datetime.utcnow() + timedelta(hours=9)
        current_time = now_jst.hour + now_jst.minute / 60.0

        def _in_range(start: float | None, end: float | None) -> bool:
            if start is None or end is None:
                return False
            return (
                (start < end and start <= current_time < end)
                or (start > end and (current_time >= start or current_time < end))
                or (start == end)
            )

        in_quiet_hours = _in_range(quiet_start, quiet_end) or _in_range(quiet2_start, quiet2_end)

        if in_quiet_hours or self.get_calendar_volatility_level() >= 3:
            exit_logic.TRAIL_ENABLED = False
        else:
            exit_logic.TRAIL_ENABLED = env_loader.get_env("TRAIL_ENABLED", "true").lower() == "true"

    def _should_peak_exit(self, side: str, indicators: dict, current_profit: float) -> bool:
        if not PEAK_EXIT_ENABLED:
            return False
        if self.max_profit_pips - current_profit < PEAK_EXIT_RETRACE_PIPS:
            return False

        from backend.strategy.signal_filter import detect_peak_reversal

        if detect_peak_reversal(self.last_candles_m5 or [], side):
            return True

        ema_fast = indicators.get("ema_fast")
        ema_slow = indicators.get("ema_slow")
        if ema_fast is None or ema_slow is None:
            return False
        if hasattr(ema_fast, "iloc"):
            if len(ema_fast) < 2 or len(ema_slow) < 2:
                return False
            prev_fast = float(ema_fast.iloc[-2])
            latest_fast = float(ema_fast.iloc[-1])
            prev_slow = float(ema_slow.iloc[-2])
            latest_slow = float(ema_slow.iloc[-1])
        else:
            if len(ema_fast) < 2 or len(ema_slow) < 2:
                return False
            prev_fast = float(ema_fast[-2])
            latest_fast = float(ema_fast[-1])
            prev_slow = float(ema_slow[-2])
            latest_slow = float(ema_slow[-1])
        cross_down = prev_fast >= prev_slow and latest_fast < latest_slow
        cross_up = prev_fast <= prev_slow and latest_fast > latest_slow
        return (side == "long" and cross_down) or (side == "short" and cross_up)

    def run(self):
        logger.info("Job Runner started.")
        while True:
            try:
                timer = PerfTimer("job_loop")
                now = datetime.utcnow()
                # ---- Market‑hours guard ---------------------------------
                if not instrument_is_tradeable(DEFAULT_PAIR):
                    logger.info(f"{DEFAULT_PAIR} market closed – sleeping 60 s")
                    time.sleep(60)
                    self.last_run = datetime.utcnow()
                    timer.stop()
                    continue
                # Refresh POSITION_REVIEW_SEC dynamically each loop
                self.review_sec = int(env_loader.get_env("POSITION_REVIEW_SEC", str(self.review_sec)))
                logger.debug(f"review_sec={self.review_sec}")
                # Refresh HIGHER_TF_ENABLED dynamically
                self.higher_tf_enabled = env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
                # Update trailing-stop enable flag each loop
                self._refresh_trailing_status()
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
                            timer.stop()
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
                    candles_h1 = candles_dict.get("H1", [])
                    candles_h4 = candles_dict.get("H4", [])
                    candles_d1 = candles_dict.get("D", [])
                    self.last_candles_m5 = candles_m5
                    candles = candles_m5  # backward compatibility
                    logger.info(f"Candle M5 last: {candles_m5[-1] if candles_m5 else 'No candles'}")

                    # -------- Higher‑timeframe reference levels --------
                    higher_tf = {}
                    if self.higher_tf_enabled:
                        higher_tf = analyze_higher_tf(DEFAULT_PAIR)
                        logger.debug(f"Higher‑TF levels: {higher_tf}")

                    # 指標計算
                    indicators_multi = calculate_indicators_multi(
                        candles_dict,
                        allow_incomplete=True,
                    )
                    self.indicators_M1 = indicators_multi.get("M1")
                    self.indicators_M5 = indicators_multi.get("M5")
                    self.indicators_M15 = indicators_multi.get("M15")
                    self.indicators_H1 = indicators_multi.get("H1")
                    self.indicators_H4 = indicators_multi.get("H4")
                    self.indicators_D = indicators_multi.get("D")
                    indicators = self.indicators_M5

                    align = is_multi_tf_aligned(
                        {
                            "M1": self.indicators_M1 or {},
                            "M5": self.indicators_M5 or {},
                            "H1": self.indicators_H1 or {},
                        }
                    )
                    if align is None and env_loader.get_env("STRICT_TF_ALIGN", "false").lower() == "true":
                        logger.info("Multi‑TF alignment missing → skip entry")
                        self.last_run = now
                        update_oanda_trades()
                        time.sleep(self.interval_seconds)
                        timer.stop()
                        continue
                    logger.info(f"Multi‑TF alignment: {align}")

                    logger.info("Indicators calculation successful.")

                    # チェック：保留LIMIT注文の更新
                    self._manage_pending_limits(DEFAULT_PAIR, indicators, candles_m5, tick_data)

                    pend_info = get_pending_entry_order(DEFAULT_PAIR)
                    if pend_info:
                        age = time.time() - pend_info.get("ts", 0)
                        if age < self.pending_grace_sec:
                            logger.info(
                                f"Pending LIMIT active ({age:.0f}s) – skip entry check"
                            )
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue

                    # ポジション確認
                    has_position = check_current_position(DEFAULT_PAIR)
                    logger.info(f"Current position status: {has_position}")
                    logger.info(f"Has open position for {DEFAULT_PAIR}: {has_position}")

                    MIN_HOLD_SEC = int(env_loader.get_env("MIN_HOLD_SEC", "0"))
                    
                    secs_since_entry = None
                    if has_position:
                        ts_raw = has_position.get("entry_time") or has_position.get("openTime")
                        if ts_raw:
                            try:
                                et = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                                secs_since_entry = (datetime.utcnow() - et).total_seconds()
                            except Exception:
                                secs_since_entry = None

                    if not has_position:
                        self.breakeven_reached = False
                        self.sl_reset_done = False
                        self.tp_extended = False
                        self.tp_reduced = False
                        self.max_profit_pips = 0.0

                    # ---- Dynamic cooldown (OPEN / FLAT) ---------------
                    # ポジション保有時はエグジット用、未保有時はエントリー用
                    if has_position:
                        self.ai_cooldown = self.ai_cooldown_flat
                    else:
                        self.ai_cooldown = self.ai_cooldown_open

                    # Determine position_side for further logic
                    if has_position and int(has_position.get("long", {}).get("units", 0)) != 0:
                        position_side = "long"
                    elif has_position and int(has_position.get("short", {}).get("units", 0)) != 0:
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
                        entry_price = float(has_position[position_side].get("averagePrice", 0.0))

                        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                        current_profit_pips = (
                            (current_price - entry_price) / pip_size
                            if position_side == "long"
                            else (entry_price - current_price) / pip_size
                        )
                        self.max_profit_pips = max(self.max_profit_pips, current_profit_pips)

                        BE_TRIGGER_PIPS = float(env_loader.get_env("BE_TRIGGER_PIPS", "10"))
                        BE_ATR_TRIGGER_MULT = float(env_loader.get_env("BE_ATR_TRIGGER_MULT", "0"))
                        BE_TRIGGER_R = float(env_loader.get_env("BE_TRIGGER_R", "0"))
                        atr_val = (
                            indicators["atr"].iloc[-1]
                            if hasattr(indicators["atr"], "iloc")
                            else indicators["atr"][-1]
                        )
                        atr_pips = atr_val / pip_size
                        if BE_ATR_TRIGGER_MULT > 0:
                            be_trigger = max(BE_TRIGGER_PIPS, atr_pips * BE_ATR_TRIGGER_MULT)
                        else:
                            be_trigger = BE_TRIGGER_PIPS
                        if BE_TRIGGER_R > 0:
                            sl_pips_val = has_position.get("sl_pips")
                            if sl_pips_val is not None:
                                try:
                                    sl_pips_val = float(sl_pips_val)
                                    be_trigger = max(be_trigger, sl_pips_val * BE_TRIGGER_R)
                                except Exception:
                                    pass
                        TP_PIPS = float(env_loader.get_env("INIT_TP_PIPS", "30"))
                        AI_PROFIT_TRIGGER_RATIO = float(env_loader.get_env("AI_PROFIT_TRIGGER_RATIO", "0.3"))

                        logger.info(
                            f"profit_pips={current_profit_pips:.1f}, "
                            f"BE_trigger={be_trigger}, "
                            f"AI_trigger={TP_PIPS * AI_PROFIT_TRIGGER_RATIO}"
                        )

                        if current_profit_pips >= be_trigger and not self.breakeven_reached:
                            adx_series = indicators.get("adx")
                            adx_val = (
                                adx_series.iloc[-1]
                                if adx_series is not None and hasattr(adx_series, "iloc")
                                else adx_series[-1] if adx_series else 0.0
                            )
                            vol_adx_min = float(env_loader.get_env("BE_VOL_ADX_MIN", "30"))
                            vol_sl_mult = float(env_loader.get_env("BE_VOL_SL_MULT", "2.0"))
                            if adx_val >= vol_adx_min:
                                if position_side == "long":
                                    new_sl_price = entry_price - atr_val * vol_sl_mult
                                else:
                                    new_sl_price = entry_price + atr_val * vol_sl_mult
                            else:
                                new_sl_price = entry_price
                            trade_id = has_position[position_side]["tradeIDs"][0]
                            result = order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                            if result is None:
                                logger.warning("SL update failed on first attempt; retrying")
                                result = order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                                if result is None:
                                    logger.error("SL update failed after retry")
                            if result is not None:
                                logger.info(f"SL updated to entry price to secure minimum profit: {new_sl_price}")
                                self.breakeven_reached = True
                                self.sl_reset_done = False
                                # SLが実行された向きと時間を記録
                                self.last_sl_side = position_side
                                self.last_sl_time = datetime.utcnow()

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
                                atr_val = (
                                    indicators["atr"].iloc[-1]
                                    if hasattr(indicators["atr"], "iloc")
                                    else indicators["atr"][-1]
                                )
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
                                    # SLが実行された向きと時間を記録
                                    self.last_sl_side = position_side
                                    self.last_sl_time = datetime.utcnow()

                        self._maybe_extend_tp(has_position, indicators, position_side, pip_size)
                        self._maybe_reduce_tp(has_position, indicators, position_side, pip_size)

                        if self._should_peak_exit(position_side, indicators, current_profit_pips):
                            logger.info("Peak exit triggered → closing position.")
                            try:
                                order_mgr.close_position(DEFAULT_PAIR, side=position_side)
                                exit_time = datetime.utcnow().isoformat()
                                log_trade(
                                    instrument=DEFAULT_PAIR,
                                    entry_time=has_position.get(
                                        "entry_time", has_position.get("openTime", exit_time)
                                    ),
                                    entry_price=entry_price,
                                    units=int(has_position[position_side]["units"]) if position_side == "long" else -int(has_position[position_side]["units"]),
                                    exit_time=exit_time,
                                    exit_price=current_price,
                                    profit_loss=float(has_position.get("pl_corrected", has_position.get("pl", 0))),
                                    ai_reason="peak exit",
                                    exit_reason=ExitReason.RISK,
                                )
                                self.last_close_ts = datetime.utcnow()
                                send_line_message(
                                    f"【PEAK EXIT】{DEFAULT_PAIR} {current_price} で決済しました。PL={current_profit_pips:.1f}pips"
                                )
                            except Exception as exc:
                                logger.warning(f"Peak exit failed: {exc}")
                            self.max_profit_pips = 0.0
                            self.breakeven_reached = False
                            self.sl_reset_done = False
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue

                        if current_profit_pips >= TP_PIPS * AI_PROFIT_TRIGGER_RATIO:
                            if secs_since_entry is not None and secs_since_entry < MIN_HOLD_SEC:
                                logger.info(
                                    f"Hold time {secs_since_entry:.1f}s < {MIN_HOLD_SEC}s → skip exit call"
                                )
                            else:
                                # EXITフィルターを評価し、フィルターNGの場合はAIの決済判断をスキップ
                                if pass_exit_filter(indicators, position_side):
                                    logger.info("Filter OK → Processing exit decision with AI.")
                                    self.last_ai_call = datetime.now()
                                    market_cond = get_market_condition(
                                        {
                                            "indicators": {
                                                key: float(val.iloc[-1]) if hasattr(val, "iloc") and val.iloc[-1] is not None
                                                else float(val) if val is not None else None
                                                for key, val in indicators.items()
                                        },
                                        "indicators_h1": {
                                            key: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                            else float(v) if v is not None else None
                                            for key, v in (self.indicators_H1 or {}).items()
                                        },
                                        "indicators_h4": {
                                            key: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                            else float(v) if v is not None else None
                                            for key, v in (self.indicators_H4 or {}).items()
                                        },
                                        "candles_m1": candles_m1,
                                        "candles_m5": candles_m5,
                                        "candles_d1": candles_d1,
                                    },
                                        higher_tf,
                                    )
                                    logger.debug(f"Market condition (exit): {market_cond}")
                                    exit_ctx = build_exit_context(
                                        has_position,
                                        tick_data,
                                        indicators,
                                        indicators_m1=self.indicators_M1,
                                    )
                                    try:
                                        ai_dec = evaluate_exit_ai(exit_ctx)
                                    except Exception as exc:
                                        logger.warning(f"exit AI evaluation failed: {exc}")
                                        ai_dec = None
                                    if ai_dec and ai_dec.action == "SCALE":
                                        try:
                                            order_mgr.enter_trade(
                                                side=position_side,
                                                lot_size=SCALE_LOT_SIZE,
                                                market_data=tick_data,
                                                strategy_params={"instrument": DEFAULT_PAIR, "mode": "market"},
                                            )
                                            logger.info(
                                                f"Scaled into position ({position_side}) by {SCALE_LOT_SIZE} lots"
                                            )
                                            has_position = check_current_position(DEFAULT_PAIR)
                                        except Exception as exc:
                                            logger.warning(f"Failed to scale position: {exc}")
                                        exit_executed = False
                                    else:
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
                    elapsed_review = None
                    if has_position and self.review_enabled:
                        if self.last_position_review_ts is None:
                            due_for_review = True
                        else:
                            elapsed_review = (now - self.last_position_review_ts).total_seconds()
                            due_for_review = elapsed_review >= self.review_sec
                        logger.debug(
                            "review check: ts=%s elapsed=%s review_sec=%s due=%s",
                            self.last_position_review_ts,
                            f"{elapsed_review:.1f}" if elapsed_review is not None else "N/A",
                            self.review_sec,
                            due_for_review,
                        )

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
                        timer.stop()
                        continue

                    # Periodic exit review
                    if has_position and due_for_review:
                        self.last_position_review_ts = now
                        logger.debug(
                            "last_position_review_ts updated to %s",
                            self.last_position_review_ts,
                        )
                        if position_side:
                            cur_price = (
                                float(tick_data["prices"][0]["bids"][0]["price"])
                                if position_side == "long"
                                else float(tick_data["prices"][0]["asks"][0]["price"])
                            )
                            entry_price = float(has_position[position_side].get("averagePrice", 0.0))
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

                        if secs_since_entry is not None and secs_since_entry < MIN_HOLD_SEC:
                            logger.info(
                                f"Hold time {secs_since_entry:.1f}s < {MIN_HOLD_SEC}s → skip exit call"
                            )
                            pass_exit = False
                        else:
                            pass_exit = pass_exit_filter(indicators, position_side)

                        if pass_exit:
                            logger.info("Filter OK → Processing periodic exit decision with AI.")
                            self.last_ai_call = datetime.now()
                            market_cond = get_market_condition(
                                {
                                    "indicators": {
                                        key: float(val.iloc[-1]) if hasattr(val, "iloc") and val.iloc[-1] is not None
                                        else float(val) if val is not None else None
                                        for key, val in indicators.items()
                                    },
                                    "indicators_h1": {
                                        key: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                        else float(v) if v is not None else None
                                        for key, v in (self.indicators_H1 or {}).items()
                                    },
                                    "indicators_h4": {
                                        key: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                        else float(v) if v is not None else None
                                        for key, v in (self.indicators_H4 or {}).items()
                                    },
                                    "candles_m1": candles_m1,
                                    "candles_m5": candles_m5,
                                    "candles_d1": candles_d1,
                                },
                                higher_tf,
                            )
                            logger.debug(f"Market condition (review): {market_cond}")
                            exit_ctx = build_exit_context(
                                has_position,
                                tick_data,
                                indicators,
                                indicators_m1=self.indicators_M1,
                            )
                            try:
                                ai_dec = evaluate_exit_ai(exit_ctx)
                            except Exception as exc:
                                logger.warning(f"exit AI evaluation failed: {exc}")
                                ai_dec = None
                            if ai_dec and ai_dec.action == "SCALE":
                                try:
                                    order_mgr.enter_trade(
                                        side=position_side,
                                        lot_size=SCALE_LOT_SIZE,
                                        market_data=tick_data,
                                        strategy_params={"instrument": DEFAULT_PAIR, "mode": "market"},
                                    )
                                    logger.info(
                                        f"Scaled into position ({position_side}) by {SCALE_LOT_SIZE} lots"
                                    )
                                    has_position = check_current_position(DEFAULT_PAIR)
                                except Exception as exc:
                                    logger.warning(f"Failed to scale position: {exc}")
                                exit_executed = False
                            else:
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
                        self.tp_extended = False
                        self.tp_reduced = False
                        self.max_profit_pips = 0.0
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
                            timer.stop()
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
                                timer.stop()
                                continue

                        # ── Entry side ───────────────────────────────
                        current_price = float(tick_data["prices"][0]["bids"][0]["price"])
                        if pass_entry_filter(
                            indicators,
                            current_price,
                            self.indicators_M1,
                            self.indicators_M15,
                            self.indicators_H1,
                        ):
                            logger.info("Filter OK → Processing entry decision with AI.")
                            self.last_ai_call = datetime.now()  # record AI call time *before* the call
                            market_cond = get_market_condition(
                                {
                                    "indicators": {
                                        key: float(val.iloc[-1]) if hasattr(val, "iloc") and val.iloc[-1] is not None
                                        else float(val) if val is not None else None
                                        for key, val in indicators.items()
                                    },
                                    "indicators_h1": {
                                        key: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                        else float(v) if v is not None else None
                                        for key, v in (self.indicators_H1 or {}).items()
                                    },
                                    "indicators_h4": {
                                        key: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None
                                        else float(v) if v is not None else None
                                        for key, v in (self.indicators_H4 or {}).items()
                                    },
                                    "candles_m1": candles_m1,
                                    "candles_m5": candles_m5,
                                    "candles_d1": candles_d1,
                                },
                                higher_tf,
                            )
                            logger.debug(f"Market condition (post‑filter): {market_cond}")

                            climax_side = detect_climax_reversal(candles_m5, indicators)
                            if climax_side and not has_position:
                                logger.info(f"Climax reversal detected → {climax_side} entry")
                                params = {
                                    "instrument": DEFAULT_PAIR,
                                    "side": climax_side,
                                    "tp_pips": float(env_loader.get_env("CLIMAX_TP_PIPS", "7")),
                                    "sl_pips": float(env_loader.get_env("CLIMAX_SL_PIPS", "10")),
                                    "mode": "market",
                                    "market_cond": market_cond,
                                }
                                order_mgr.enter_trade(
                                    side=climax_side,
                                    lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
                                    market_data=tick_data,
                                    strategy_params=params,
                                )
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue

                            if filter_pre_ai(candles_m5, indicators, market_cond):
                                logger.info("Pre-AI filter triggered → skipping entry.")
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue

                            if not has_position and market_cond.get("market_condition") == "break":
                                try:
                                    direction = market_cond.get("range_break")
                                    follow = follow_breakout(candles_m5, indicators, direction)
                                    logger.info(f"follow_breakout result: {follow}")
                                except Exception as exc:
                                    logger.warning(f"follow_breakout failed: {exc}")

                            margin_used = get_margin_used()
                            logger.info(f"marginUsed={margin_used}")
                            if margin_used is None:
                                logger.warning("Failed to obtain marginUsed")
                            elif MARGIN_WARNING_THRESHOLD > 0 and margin_used > MARGIN_WARNING_THRESHOLD:
                                logger.warning(
                                    f"marginUsed {margin_used} exceeds threshold {MARGIN_WARNING_THRESHOLD}"
                                )

                            # --- SL hit cooldown check ----------------------
                            try:
                                plan_check = get_trade_plan(
                                    tick_data,
                                    {"M5": indicators},
                                    {"M1": candles_m1, "M5": candles_m5},
                                    patterns=PATTERN_NAMES,
                                    detected_patterns=self.patterns_by_tf,
                                )
                                side = plan_check.get("entry", {}).get("side", "no").lower()
                            except Exception as exc:
                                logger.warning(f"get_trade_plan failed for check: {exc}")
                                side = "no"

                            cooldown = int(env_loader.get_env("SL_COOLDOWN_SEC", str(self.sl_cooldown_sec)))
                            if (
                                side in ("long", "short")
                                and self.last_sl_time
                                and (now - self.last_sl_time).total_seconds() < cooldown
                                and side == self.last_sl_side
                            ):
                                logger.info(
                                    f"Entry blocked: recent SL hit on {side}. Cooldown {(now - self.last_sl_time).total_seconds():.0f}s < {cooldown}s"
                                )
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue

                            if side == "long" and consecutive_lower_lows(candles_m5):
                                logger.info("Entry blocked: consecutive lower lows detected")
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue

                            if counter_trend_block(side, indicators, self.indicators_M15, self.indicators_H1):
                                logger.info("Counter-trend block triggered → skip entry")
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue

                            result = process_entry(
                                indicators,
                                candles_m5,
                                tick_data,
                                market_cond,
                                higher_tf=higher_tf,
                                patterns=PATTERN_NAMES,
                                candles_dict={"M1": candles_m1, "M5": candles_m5},
                                pattern_names=self.patterns_by_tf,
                                tf_align=align,
                            )
                            if not result:
                                pend = get_pending_entry_order(DEFAULT_PAIR)
                                if pend and pend.get("order_id"):
                                    age = time.time() - pend.get("ts", 0)
                                    if age >= self.pending_grace_sec:
                                        try:
                                            order_mgr.cancel_order(pend["order_id"])
                                            logger.info(
                                                f"AI declined entry; canceled pending LIMIT {pend['order_id']}"
                                            )
                                        except Exception as exc:
                                            logger.warning(
                                                f"Failed to cancel pending LIMIT {pend['order_id']}: {exc}"
                                            )
                                        for key, info in list(_pending_limits.items()):
                                            if info.get("order_id") == pend["order_id"]:
                                                _pending_limits.pop(key, None)
                                                break
                                    else:
                                        logger.info(
                                            f"Pending LIMIT age {age:.0f}s < grace period; keeping order"
                                        )
                                logger.info(
                                    "process_entry returned False → aborting entry and continuing loop"
                                )
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
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
                timer.stop()

            except Exception as e:
                logger.error(f"Error occurred during job execution: {e}", exc_info=True)
                time.sleep(self.interval_seconds)


if __name__ == "__main__":
    runner = JobRunner(interval_seconds=1)
    runner.run()
