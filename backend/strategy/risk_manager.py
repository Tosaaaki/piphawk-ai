"""Risk management helper functions."""
from __future__ import annotations

from typing import Optional

try:
    from risk.portfolio_risk_manager import PortfolioRiskManager
except Exception:  # pragma: no cover - optional dependency during tests
    PortfolioRiskManager = None  # type: ignore


def calc_lot_size(
    balance: float,
    risk_pct: float,
    sl_pips: float,
    pip_value: float,
    risk_engine: Optional[PortfolioRiskManager] = None,
) -> float:
    """Return allowed lot size based on account balance and risk percent."""
    if risk_engine is not None:
        return risk_engine.get_allowed_lot(balance, risk_pct, sl_pips, pip_value)
    if sl_pips <= 0 or pip_value <= 0:
        raise ValueError("sl_pips and pip_value must be positive")
    risk_amount = balance * risk_pct
    return risk_amount / (sl_pips * pip_value)
