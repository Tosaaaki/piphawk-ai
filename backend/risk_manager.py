import logging

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


def is_high_vol_session() -> bool:
    """ロンドン・NY序盤などボラティリティが高い時間帯か判定する。"""
    from datetime import datetime, timedelta

    now_jst = datetime.utcnow() + timedelta(hours=9)
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


def cost_guard(tp_pips: float | None, spread_pips: float) -> bool:
    """Return True if net take-profit after spread meets threshold."""
    from backend.utils import env_loader

    try:
        tp = float(tp_pips) if tp_pips is not None else None
        spread = float(spread_pips)
        if tp is None:
            return True
        min_net = float(env_loader.get_env("MIN_NET_TP_PIPS", "1"))
        return (tp - spread) >= min_net
    except Exception:
        return True

