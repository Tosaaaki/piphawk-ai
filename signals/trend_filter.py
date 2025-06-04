"""Multi timeframe EMA trend filter."""
from __future__ import annotations

from typing import Optional


def trend_direction_allowed(side: str, price: float, ema_h1: Optional[float], ema_h4: Optional[float]) -> bool:
    """Return True if order side is allowed based on higher timeframe EMAs."""
    if side == "long":
        if ema_h1 is not None and price < ema_h1:
            return False
        if ema_h4 is not None and price < ema_h4:
            return False
    elif side == "short":
        if ema_h1 is not None and price > ema_h1:
            return False
        if ema_h4 is not None and price > ema_h4:
            return False
    return True

__all__ = ["trend_direction_allowed"]
