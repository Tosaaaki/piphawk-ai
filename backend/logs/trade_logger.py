from __future__ import annotations

from enum import Enum
from typing import Any
import json

from .log_manager import log_trade as _log_trade, log_policy_transition


class ExitReason(Enum):
    AI = "AI"
    RISK = "RISK"
    DUPLICATION = "DUPLICATION"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


def log_trade(
    *,
    exit_reason: ExitReason | None = None,
    is_manual: bool | None = None,
    strategy_name: str | None = None,
    state: dict | None = None,
    reward: float | None = None,
    **kwargs: Any,
) -> None:
    """Wrapper for log_trade allowing ``ExitReason`` enumeration and RL logging."""
    if exit_reason is not None:
        kwargs["exit_reason"] = exit_reason.value
    if is_manual is not None:
        kwargs["is_manual"] = is_manual
    _log_trade(**kwargs)
    if strategy_name and state is not None and reward is not None:
        log_policy_transition(json.dumps(state), strategy_name, float(reward))
