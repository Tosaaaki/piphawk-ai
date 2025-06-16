import logging

from backend.utils import env_loader

logger = logging.getLogger(__name__)


def validate_sl(tp_pips: float, sl_pips: float, atr: float, min_atr_mult: float) -> bool:
    """ATRとの比較に基づきSLが適切か検証する。"""
    try:
        if sl_pips < atr * min_atr_mult:
            logger.warning("SL too tight (%.1fpips < %.1f)", sl_pips, atr * min_atr_mult)
            return False
    except Exception:
        return False
    return True


def validate_rrr(tp_pips: float, sl_pips: float, min_rrr: float) -> bool:
    """Return True if tp_pips / sl_pips meets or exceeds min_rrr."""
    try:
        return sl_pips > 0 and (tp_pips / sl_pips) >= min_rrr
    except Exception:
        return False


def validate_rrr_after_cost(
    tp_pips: float, sl_pips: float, cost_pips: float, min_rrr: float
) -> bool:
    """Return True if (tp_pips - cost_pips) / sl_pips >= min_rrr."""
    try:
        net_tp = tp_pips - cost_pips
        return sl_pips > 0 and (net_tp / sl_pips) >= min_rrr
    except Exception:
        return False


def is_high_vol_session() -> bool:
    """ロンドン・NY序盤などボラティリティが高い時間帯か判定する。"""
    from datetime import datetime, timedelta, timezone

    now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
    hour = now_jst.hour + now_jst.minute / 60.0
    return (15 <= hour < 17) or (22 <= hour < 24)


def get_recent_swing_diff(
    candles: list[dict], side: str, entry_price: float, pip_size: float, lookback: int = 20
) -> float | None:
    """直近スイング高安までの距離(pips)を計算する。"""
    highs: list[float] = []
    lows: list[float] = []
    for c in candles[-lookback:]:
        base = c.get("mid", c)
        try:
            highs.append(float(base.get("h")))
            lows.append(float(base.get("l")))
        except Exception:
            return None
    if not highs or not lows:
        return None

    if side == "long":
        swing = min(lows)
    else:
        swing = max(highs)
    return abs(entry_price - swing) / pip_size


def calc_min_sl(
    atr_pips: float | None,
    swing_diff: float | None,
    *,
    atr_mult: float = 1.2,
    swing_buffer_pips: float = 5.0,
    session_factor: float = 1.0,
) -> float:
    """ATRとスイング距離に基づき最小SL幅を算出する。"""
    atr_val = atr_pips * atr_mult * session_factor if atr_pips is not None else 0.0
    swing_val = swing_diff + swing_buffer_pips if swing_diff is not None else 0.0
    return max(atr_val, swing_val)


def calc_short_sl_price(
    swing_high: float | None, atr_pips: float | None, pip_size: float
) -> float | None:
    """Return short position SL price based on swing high and ATR."""
    if swing_high is None or atr_pips is None:
        return None
    try:
        return swing_high + (atr_pips * 0.5) * pip_size
    except Exception:
        return None

def cost_guard(tp_pips: float | None, spread_pips: float, *, noise_pips: float | None = None) -> bool:
    """Return True if net take-profit after spread meets threshold."""
    from backend.utils import env_loader

    try:
        tp = float(tp_pips) if tp_pips is not None else None
        spread = float(spread_pips)
        if tp is None:
            return True
        base_min = float(env_loader.get_env("MIN_NET_TP_PIPS", "1"))
        if noise_pips is not None:
            base_min = max(base_min, float(noise_pips) * 0.6)
        return (tp - spread) >= base_min
    except Exception:
        return True


def calc_fallback_tp_sl(indicators: dict, pip_size: float) -> tuple[float | None, float | None]:
    """ATRやBB幅からTP/SLを算出する補助関数"""
    atr_series = indicators.get("atr")
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")

    atr_pips = None
    if atr_series is not None and len(atr_series):
        try:
            atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            atr_pips = float(atr_val) / pip_size
        except Exception:
            atr_pips = None

    tp = sl = None
    try:
        mult_tp = float(env_loader.get_env("ATR_MULT_TP", "0.8"))
        mult_sl = float(env_loader.get_env("ATR_MULT_SL", "1.1"))
        if atr_pips is not None:
            tp = atr_pips * mult_tp
            sl = atr_pips * mult_sl
    except Exception:
        pass

    if tp is None and bb_upper is not None and bb_lower is not None:
        try:
            up = bb_upper.iloc[-1] if hasattr(bb_upper, "iloc") else bb_upper[-1]
            low = bb_lower.iloc[-1] if hasattr(bb_lower, "iloc") else bb_lower[-1]
            width = float(up) - float(low)
            ratio = float(env_loader.get_env("TP_BB_RATIO", "0.6"))
            tp = width / pip_size * ratio
        except Exception:
            pass

    return tp, sl


def tp_only_condition(sl_pips: float | None, noise_pips: float | None) -> bool:
    """Return True if SL is below noise threshold and should be omitted."""
    try:
        coeff = float(env_loader.get_env("TP_ONLY_NOISE_MULT", "0"))
        return (
            coeff > 0
            and sl_pips is not None
            and noise_pips is not None
            and float(sl_pips) < float(noise_pips) * coeff
        )
    except Exception:
        return False


