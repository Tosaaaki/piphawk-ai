from __future__ import annotations

"""Compatibility wrapper for mode_hybrid."""

from .mode_hybrid import MarketContext, detect_mode, detect_mode_simple, load_config

__all__ = [
    "MarketContext",
    "detect_mode",
    "detect_mode_simple",
    "load_config",
]
