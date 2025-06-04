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

