"""Simple vertical ensemble buffer for entry plans."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from backend.utils import env_loader

from .ai_entry_plan import EntryPlan

ENTRY_BUFFER_K = int(env_loader.get_env("ENTRY_BUFFER_K", "3"))


@dataclass
class PlanBuffer:
    _buf: deque[EntryPlan]

    def __init__(self) -> None:
        self._buf = deque(maxlen=ENTRY_BUFFER_K)

    def append(self, plan: EntryPlan) -> None:
        self._buf.append(plan)

    def average(self) -> EntryPlan | None:
        if len(self._buf) < ENTRY_BUFFER_K:
            return None
        tp = sum(p.tp for p in self._buf) / ENTRY_BUFFER_K
        sl = sum(p.sl for p in self._buf) / ENTRY_BUFFER_K
        side = (
            self._buf[0].side if all(p.side == self._buf[0].side for p in self._buf) else "none"
        )
        lot = sum(p.lot for p in self._buf) / ENTRY_BUFFER_K
        return EntryPlan(side=side, tp=tp, sl=sl, lot=lot)

__all__ = ["PlanBuffer"]
