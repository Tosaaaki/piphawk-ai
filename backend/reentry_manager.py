from __future__ import annotations

from datetime import datetime, timezone
from backend.utils import env_loader


class ReentryManager:
    """SL直後の再エントリー判定を行うヘルパー。"""

    def __init__(self, trigger_pips_over_break: float | None = None) -> None:
        self.trigger_pips_over_break = float(
            trigger_pips_over_break
            if trigger_pips_over_break is not None
            else env_loader.get_env("REENTRY_TRIGGER_PIPS", "1")
        )
        self.sl_hit_time: datetime | None = None
        self.sl_hit_price: float | None = None
        self.side: str | None = None

    def record_sl_hit(self, price: float, side: str) -> None:
        """SLが実行された価格と方向を記録する。"""
        self.sl_hit_time = datetime.now(timezone.utc)
        self.sl_hit_price = float(price)
        self.side = side

    def should_reenter(self, price: float, spread: float = 0.0) -> bool:
        """SL直後の価格が一定幅を超えて戻ったかを判定する。"""
        if self.sl_hit_price is None or self.side is None:
            return False

        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        threshold = spread + self.trigger_pips_over_break * pip_size
        diff = price - self.sl_hit_price

        if self.side == "long" and diff > threshold:
            self.sl_hit_time = None
            self.sl_hit_price = None
            self.side = None
            return True
        if self.side == "short" and -diff > threshold:
            self.sl_hit_time = None
            self.sl_hit_price = None
            self.side = None
            return True
        return False
