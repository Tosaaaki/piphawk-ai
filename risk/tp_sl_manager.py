"""TP/SL ratio adjustment utilities."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def adjust_sl_for_rr(tp_pips: float, sl_pips: float, min_rr: float) -> tuple[float, float]:
    """Return (tp_pips, sl_pips) ensuring TP/SL ratio >= min_rr.

    If the ratio is below ``min_rr``, the SL value will be reduced
    to ``tp_pips / min_rr`` while TP remains unchanged.
    """
    try:
        if sl_pips <= 0:
            return tp_pips, sl_pips
        current_rr = tp_pips / sl_pips
        if current_rr < min_rr:
            new_sl = tp_pips / min_rr
            logger.warning(
                "RR %.2f below %.2f – shrinking SL from %.2f to %.2f",
                current_rr,
                min_rr,
                sl_pips,
                new_sl,
            )
            return tp_pips, new_sl
    except Exception as exc:
        logger.debug("adjust_sl_for_rr failed: %s", exc)
    return tp_pips, sl_pips


__all__ = ["adjust_sl_for_rr"]
