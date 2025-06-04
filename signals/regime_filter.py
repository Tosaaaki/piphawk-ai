"""Regime conflict blocker."""
from __future__ import annotations

from typing import Optional


def pass_regime_filter(local_dir: Optional[str], ai_dir: Optional[str]) -> bool:
    """Return False when local_dir and ai_dir are both present and differ."""
    if local_dir and ai_dir and local_dir != ai_dir:
        return False
    return True

__all__ = ["pass_regime_filter"]
