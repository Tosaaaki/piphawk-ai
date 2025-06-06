"""Simple backtest helper."""
from __future__ import annotations

from typing import Sequence


def run_simple_backtest(prices: Sequence[float], signals: Sequence[int]) -> dict:
    """Return equity curve and summary for long=1, short=-1 signals."""
    if len(prices) != len(signals):
        raise ValueError("prices and signals length mismatch")
    equity = 0.0
    curve = []
    for price, sig in zip(prices, signals):
        equity += sig * price
        curve.append(equity)
    trades = sum(1 for s in signals if s != 0)
    return {"equity_curve": curve, "trades": trades, "final_equity": equity}

__all__ = ["run_simple_backtest"]
