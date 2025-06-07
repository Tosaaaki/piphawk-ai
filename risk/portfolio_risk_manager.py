from __future__ import annotations

"""CVaRベースのポートフォリオリスク管理エンジン."""

from typing import Sequence

from .cvar import calc_cvar
from backend.strategy import risk_manager as strat_rm


class PortfolioRiskManager:
    """シンプルなポートフォリオリスク管理クラス."""

    def __init__(self, max_cvar: float, alpha: float = 0.05) -> None:
        self.max_cvar = float(max_cvar)
        self.alpha = float(alpha)
        self.current_cvar = 0.0

    def update_risk_metrics(
        self, trade_log: Sequence[float], open_positions: Sequence[float] | None = None
    ) -> None:
        """実現損益と含み損益からCVaRを計算する."""
        returns: list[float] = list(trade_log)
        if open_positions:
            returns.extend(open_positions)
        if returns:
            self.current_cvar = calc_cvar(returns, self.alpha)
        else:
            self.current_cvar = 0.0

    def check_stop_conditions(self) -> bool:
        """許容CVaRを超過したかを判定する."""
        return abs(self.current_cvar) >= self.max_cvar

    def get_allowed_lot(
        self,
        balance: float,
        risk_pct: float,
        sl_pips: float,
        pip_value: float,
    ) -> float:
        """現在のリスク水準に基づきロット数を返す."""
        base = strat_rm.calc_lot_size(balance, risk_pct, sl_pips, pip_value)
        if self.check_stop_conditions():
            return 0.0
        factor = max(0.0, 1.0 - abs(self.current_cvar) / self.max_cvar)
        return base * factor

__all__ = ["PortfolioRiskManager"]
