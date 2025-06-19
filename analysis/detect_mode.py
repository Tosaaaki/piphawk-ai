from __future__ import annotations

"""Local trade mode detection utilities."""

from dataclasses import dataclass
from typing import Sequence


@dataclass
class MarketContext:
    """Market context result container."""

    mode: str
    score: float
    reasons: list[str]


def detect_mode(indicators: dict, candles: Sequence[dict] | None = None) -> MarketContext:
    """Return market context using local heuristics.

    Parameters
    ----------
    indicators : dict
        Indicator dictionary.
    candles : Sequence[dict] | None, optional
        M5 candles or similar. Only close and open prices are used.

    Returns
    -------
    MarketContext
        Detected mode, score and reasons.
    """
    from signals.composite_mode import decide_trade_mode_detail
    mode, score, reasons = decide_trade_mode_detail(indicators, candles)
    return MarketContext(mode=mode, score=score, reasons=reasons)


__all__ = ["detect_mode", "MarketContext"]
