"""Manage cooldown after stop-loss exits."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


class ReentryManager:
    def __init__(self, cooldown_sec: int = 300):
        self.cooldown = timedelta(seconds=cooldown_sec)
        self.last_exit: dict[str, datetime] = {}

    def record_stop(self, side: str, ts: datetime | None = None) -> None:
        """Register a stop-loss exit for the given side."""
        self.last_exit[side] = ts or datetime.now(timezone.utc)

    def can_enter(self, side: str, ts: datetime | None = None) -> bool:
        """Return True if enough time has passed since the last stop-loss."""
        last = self.last_exit.get(side)
        if not last:
            return True
        now = ts or datetime.now(timezone.utc)
        return now - last >= self.cooldown
