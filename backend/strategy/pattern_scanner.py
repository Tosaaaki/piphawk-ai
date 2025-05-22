# Local and AI-based chart pattern scanner
from __future__ import annotations

from typing import Dict, List, Optional

from backend.utils import env_loader
from backend.strategy.pattern_ai_detection import detect_chart_pattern

PATTERN_SCAN_MODE = env_loader.get_env("PATTERN_SCAN_MODE", "ai").lower()


def _price(candle: dict, key: str) -> Optional[float]:
    if key in candle:
        try:
            return float(candle[key])
        except (TypeError, ValueError):
            return None
    mid = candle.get("mid")
    if isinstance(mid, dict):
        try:
            return float(mid.get(key))
        except (TypeError, ValueError):
            return None
    return None


def _detect_double_bottom(candles: List[dict]) -> bool:
    if len(candles) < 3:
        return False
    l1 = _price(candles[-3], "l")
    l2 = _price(candles[-1], "l")
    if l1 is None or l2 is None:
        return False
    return abs(l1 - l2) <= max(abs(l1), abs(l2)) * 0.002 and _price(candles[-2], "h") is not None


def _detect_double_top(candles: List[dict]) -> bool:
    if len(candles) < 3:
        return False
    h1 = _price(candles[-3], "h")
    h2 = _price(candles[-1], "h")
    if h1 is None or h2 is None:
        return False
    return abs(h1 - h2) <= max(abs(h1), abs(h2)) * 0.002 and _price(candles[-2], "l") is not None


def detect_local_pattern(candles: List[dict], patterns: List[str]) -> Optional[str]:
    if "double_bottom" in patterns and _detect_double_bottom(candles):
        return "double_bottom"
    if "double_top" in patterns and _detect_double_top(candles):
        return "double_top"
    return None


def scan(candles_dict: Dict[str, List[dict]], patterns: List[str], mode: str | None = None) -> Dict[str, Optional[str]]:
    """Scan multiple timeframes and return detected pattern names."""
    mode = (mode or PATTERN_SCAN_MODE).lower()
    results: Dict[str, Optional[str]] = {}
    for tf, candles in candles_dict.items():
        pattern = None
        if mode == "ai":
            try:
                res = detect_chart_pattern(candles, patterns)
                pattern = res.get("pattern")
            except Exception:
                pattern = None
        else:
            pattern = detect_local_pattern(candles, patterns)
        results[tf] = pattern
    return results
