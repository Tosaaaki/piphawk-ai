"""CVaR-based portfolio risk management."""
from typing import Sequence

from piphawk_ai.risk.cvar import calc_cvar


class PortfolioRiskManager:
    """Simple portfolio risk management class."""

    def __init__(self, max_cvar: float, alpha: float = 0.05) -> None:
        self.max_cvar = float(max_cvar)
        self.alpha = float(alpha)
        self.current_cvar = 0.0

    def update_risk_metrics(
        self,
        trade_log: Sequence[float],
        open_positions: Sequence[float] | None = None,
    ) -> None:
        """Compute CVaR from realized and unrealized P/L."""
        returns: list[float] = list(trade_log)
        if open_positions:
            returns.extend(open_positions)
        self.current_cvar = calc_cvar(returns, self.alpha) if returns else 0.0

    def check_stop_conditions(self) -> bool:
        """Return True if the current CVaR exceeds the allowed maximum."""
        return abs(self.current_cvar) >= self.max_cvar

    def get_allowed_lot(
        self,
        balance: float,
        risk_pct: float,
        sl_pips: float,
        pip_value: float,
    ) -> float:
        """Return lot size allowed under current risk level."""
        if sl_pips <= 0 or pip_value <= 0:
            raise ValueError("sl_pips and pip_value must be positive")
        risk_amount = balance * risk_pct
        base = risk_amount / (sl_pips * pip_value)
        if self.check_stop_conditions():
            return 0.0
        factor = max(0.0, 1.0 - abs(self.current_cvar) / self.max_cvar)
        return base * factor

__all__ = ["PortfolioRiskManager"]
