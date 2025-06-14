from __future__ import annotations

import json
from enum import Enum
from typing import Any

try:
    from .log_manager import (
        add_trade_label,
        log_policy_transition,
    )
    from .log_manager import log_trade as _log_trade
except Exception:  # pragma: no cover - log_manager may be stubbed
    from .log_manager import add_trade_label
    from .log_manager import log_trade as _log_trade

    def log_policy_transition(*_a, **_k):
        return None


from backend.utils import env_loader


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
    if "score_version" not in kwargs:
        kwargs["score_version"] = int(env_loader.get_env("SCORE_VERSION", "1"))
    trade_id = _log_trade(**kwargs)
    if trade_id is not None:
        if kwargs.get("exit_time") is not None:
            add_trade_label(trade_id, "EXIT")
        else:
            add_trade_label(trade_id, "ENTRY")
    if strategy_name and state is not None and reward is not None:
        log_policy_transition(json.dumps(state), strategy_name, float(reward))
