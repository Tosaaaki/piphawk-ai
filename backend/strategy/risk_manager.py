"""Risk management helper functions."""
from __future__ import annotations


def calc_lot_size(balance: float, risk_pct: float, sl_pips: float, pip_value: float) -> float:
    """Return allowed lot size based on account balance and risk percent."""
    if sl_pips <= 0 or pip_value <= 0:
        raise ValueError("sl_pips and pip_value must be positive")
    risk_amount = balance * risk_pct
    return risk_amount / (sl_pips * pip_value)
