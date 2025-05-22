"""Simple local chart pattern detector."""

from __future__ import annotations

from typing import List, Dict


def pattern_scanner(candles: List[Dict], patterns: List[str]) -> Dict[str, str | None]:
    """Return the first pattern name if candles are available.

    This is a placeholder implementation that simply returns the first requested
    pattern when candle data is present. If no candles or patterns are provided,
    ``{"pattern": None}`` is returned.
    """

    if not candles or not patterns:
        return {"pattern": None}

    # TODO: implement real scanning logic
    return {"pattern": patterns[0]}
