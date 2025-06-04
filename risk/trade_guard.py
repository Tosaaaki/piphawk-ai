"""Simple losing streak guard."""
from __future__ import annotations


class TradeGuard:
    """Track consecutive losses to pause trading."""

    def __init__(self, max_losses: int = 3) -> None:
        self.max_losses = max_losses
        self.loss_streak = 0

    def record_result(self, profit_loss: float) -> None:
        if profit_loss < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0

    def can_trade(self) -> bool:
        return self.loss_streak < self.max_losses

__all__ = ["TradeGuard"]
