from __future__ import annotations

"""Utility helper for trade timestamps."""

from datetime import datetime
from typing import Any, Optional


def trade_age_seconds(trade: dict[str, Any], *, now: Optional[datetime] = None) -> float | None:
    """Return the age of *trade* in seconds based on entry_time or openTime."""
    ts = trade.get("entry_time") or trade.get("openTime")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None
    now = now or datetime.utcnow()
    return (now - dt).total_seconds()

