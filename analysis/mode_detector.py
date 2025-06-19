from __future__ import annotations

"""Compatibility wrapper for mode_hybrid."""

try:
    # When imported as a package module
    from .mode_hybrid import MarketContext, detect_mode, detect_mode_simple, load_config
except ImportError:  # pragma: no cover - fallback for direct execution
    # Fallback to absolute import when executed as a script
    from analysis.mode_hybrid import (
        MarketContext,
        detect_mode,
        detect_mode_simple,
        load_config,
    )

__all__ = [
    "MarketContext",
    "detect_mode",
    "detect_mode_simple",
    "load_config",
]
