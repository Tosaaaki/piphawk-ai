"""Exit-related helpers for JobRunner."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.utils import env_loader
from backend.strategy import exit_logic

__all__ = [
    "maybe_extend_tp",
    "maybe_reduce_tp",
    "refresh_trailing_status",
    "should_peak_exit",
    "get_calendar_volatility_level",
]

def maybe_extend_tp(runner: Any, position: dict, indicators: dict, side: str, pip_size: float) -> None:
    if runner.tp_extended or not runner.TP_EXTENSION_ENABLED:
        return
    adx_series = indicators.get("adx")
    atr_series = indicators.get("atr")
    if adx_series is None or atr_series is None:
        return
    adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
    if adx_val < runner.TP_EXTENSION_ADX_MIN:
        return
    atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
    ext_pips = (atr_val / pip_size) * runner.TP_EXTENSION_ATR_MULT
    try:
        entry_price = float(position[side].get("averagePrice", 0.0))
        trade_id = position[side]["tradeIDs"][0]
        er_raw = position.get("entry_regime")
        entry_uuid = json.loads(er_raw).get("entry_uuid") if er_raw else None
    except Exception:
        return
    new_tp = entry_price + ext_pips * pip_size if side == "long" else entry_price - ext_pips * pip_size
    current_tp = runner.order_mgr.get_current_tp(trade_id) if hasattr(runner.order_mgr, "get_current_tp") else None
    if current_tp is not None and abs(current_tp - new_tp) < pip_size * 0.1:
        return
    try:
        res = runner.order_mgr.adjust_tp_sl(
            runner.DEFAULT_PAIR,
            trade_id,
            new_tp=new_tp,
            entry_uuid=entry_uuid,
        )
        if res is not None:
            runner.logger.info(
                f"TP extended from {current_tp} to {new_tp} ({ext_pips:.1f}pips) due to strong trend"
            )
            runner.tp_extended = True
    except Exception as exc:
        runner.logger.warning(f"TP extension failed: {exc}")

def maybe_reduce_tp(runner: Any, position: dict, indicators: dict, side: str, pip_size: float) -> None:
    if runner.tp_reduced or not runner.TP_REDUCTION_ENABLED:
        return
    adx_series = indicators.get("adx")
    atr_series = indicators.get("atr")
    if adx_series is None or atr_series is None:
        return
    adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
    if adx_val > runner.TP_REDUCTION_ADX_MAX:
        return
    entry_ts = position.get("entry_time") or position.get("openTime")
    if entry_ts:
        try:
            et = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
            held_sec = (datetime.now(timezone.utc) - et).total_seconds()
            if held_sec < runner.TP_REDUCTION_MIN_SEC:
                return
        except Exception:
            pass
    atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
    red_pips = (atr_val / pip_size) * runner.TP_REDUCTION_ATR_MULT
    try:
        entry_price = float(position[side].get("averagePrice", 0.0))
        trade_id = position[side]["tradeIDs"][0]
        er_raw = position.get("entry_regime")
        entry_uuid = json.loads(er_raw).get("entry_uuid") if er_raw else None
    except Exception:
        return
    new_tp = entry_price + red_pips * pip_size if side == "long" else entry_price - red_pips * pip_size
    current_tp = runner.order_mgr.get_current_tp(trade_id) if hasattr(runner.order_mgr, "get_current_tp") else None
    if current_tp is not None and abs(current_tp - new_tp) < pip_size * 0.1:
        return
    try:
        res = runner.order_mgr.adjust_tp_sl(
            runner.DEFAULT_PAIR,
            trade_id,
            new_tp=new_tp,
            entry_uuid=entry_uuid,
        )
        if res is not None:
            runner.logger.info(
                f"TP reduced from {current_tp} to {new_tp} ({red_pips:.1f}pips) due to weak trend"
            )
            runner.tp_reduced = True
    except Exception as exc:
        runner.logger.warning(f"TP reduction failed: {exc}")

def get_calendar_volatility_level() -> int:
    try:
        return int(env_loader.get_env("CALENDAR_VOLATILITY_LEVEL", "0"))
    except (TypeError, ValueError):
        return 0

def refresh_trailing_status(runner: Any) -> None:
    quiet_start = float(env_loader.get_env("QUIET_START_HOUR_JST", "3"))
    quiet_end = float(env_loader.get_env("QUIET_END_HOUR_JST", "7"))
    quiet2_enabled = env_loader.get_env("QUIET2_ENABLED", "false").lower() == "true"
    if quiet2_enabled:
        quiet2_start = float(env_loader.get_env("QUIET2_START_HOUR_JST", "23"))
        quiet2_end = float(env_loader.get_env("QUIET2_END_HOUR_JST", "1"))
    else:
        quiet2_start = quiet2_end = None

    now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
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

    if in_quiet_hours or get_calendar_volatility_level() >= 3:
        exit_logic.TRAIL_ENABLED = False
    else:
        exit_logic.TRAIL_ENABLED = env_loader.get_env("TRAIL_ENABLED", "true").lower() == "true"

def should_peak_exit(runner: Any, side: str, indicators: dict, current_profit: float) -> bool:
    if not runner.PEAK_EXIT_ENABLED:
        return False
    atr_val = indicators.get("atr")
    if hasattr(atr_val, "iloc"):
        atr_val = float(atr_val.iloc[-1])
    if atr_val is None:
        return False
    pip_size = 0.01 if runner.DEFAULT_PAIR.endswith("_JPY") else 0.0001
    allowed_draw = (atr_val / pip_size) * runner.MM_DRAW_MAX_ATR_RATIO
    if (runner.max_profit_pips - current_profit) < allowed_draw:
        return False
    from backend.strategy.signal_filter import detect_peak_reversal
    if detect_peak_reversal(runner.last_candles_m5 or [], side):
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
