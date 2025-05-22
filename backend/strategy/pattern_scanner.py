import math
import os
from typing import Iterable, Mapping

CANDLE_KEYS = ('o', 'h', 'l', 'c')

# Pattern detection tunables
PATTERN_MIN_BARS = int(os.getenv("PATTERN_MIN_BARS", "5"))
PATTERN_TOLERANCE = float(os.getenv("PATTERN_TOLERANCE", "0.005"))

def _as_list(data: Iterable[Mapping]) -> list[dict]:
    return [
        {k: float(row.get(k, 0)) for k in CANDLE_KEYS}
        for row in data
    ]

def _is_close(a: float, b: float, tol: float = PATTERN_TOLERANCE) -> bool:
    return abs(a - b) <= tol

def detect_double_bottom(data: list[dict]) -> bool:
    if len(data) < PATTERN_MIN_BARS:
        return False
    lows = [row['l'] for row in data]
    highs = [row['h'] for row in data]
    i1 = lows.index(min(lows))
    try:
        sub = lows[i1+1:]
        i2 = sub.index(min(sub)) + i1 + 1
    except ValueError:
        return False
    if i2 - i1 < 2:
        return False
    if not _is_close(lows[i1], lows[i2]):
        return False
    hi_between = max(highs[i1+1:i2]) if i2-i1>1 else lows[i1]
    hi_after = max(highs[i2+1:]) if i2+1 < len(highs) else lows[i2]
    return hi_after > hi_between

def detect_double_top(data: list[dict]) -> bool:
    if len(data) < PATTERN_MIN_BARS:
        return False
    highs = [row['h'] for row in data]
    lows = [row['l'] for row in data]
    i1 = highs.index(max(highs))
    for j in range(i1 + 2, len(highs)):
        if _is_close(highs[j], highs[i1]):
            lo_between = min(lows[i1 + 1:j])
            lo_after = min(lows[j + 1:]) if j + 1 < len(lows) else lo_between - 0.01
            if lo_after < lo_between:
                return True
    return False


def _find_max_index(seq: list[float]) -> int:
    return seq.index(max(seq)) if seq else -1


def _find_min_index(seq: list[float]) -> int:
    return seq.index(min(seq)) if seq else -1


def detect_head_and_shoulders(data: list[dict]) -> bool:
    """Very naive head-and-shoulders detection."""
    if len(data) < max(PATTERN_MIN_BARS, 5):
        return False
    highs = [row['h'] for row in data]
    head_idx = _find_max_index(highs)
    if head_idx in (0, len(highs) - 1):
        return False
    left_idx = _find_max_index(highs[:head_idx])
    right_idx = _find_max_index(highs[head_idx + 1:])
    if left_idx < 0 or right_idx < 0:
        return False
    right_idx += head_idx + 1
    left = highs[left_idx]
    right = highs[right_idx]
    head = highs[head_idx]
    if head <= left or head <= right:
        return False
    if not _is_close(left, right, tol=head * 0.05):
        return False
    return True


def detect_inverse_head_and_shoulders(data: list[dict]) -> bool:
    """Inverse head-and-shoulders pattern."""
    if len(data) < max(PATTERN_MIN_BARS, 5):
        return False
    lows = [row['l'] for row in data]
    head_idx = _find_min_index(lows)
    if head_idx in (0, len(lows) - 1):
        return False
    left_idx = _find_min_index(lows[:head_idx])
    right_idx = _find_min_index(lows[head_idx + 1:])
    if left_idx < 0 or right_idx < 0:
        return False
    right_idx += head_idx + 1
    left = lows[left_idx]
    right = lows[right_idx]
    head = lows[head_idx]
    if head >= left or head >= right:
        return False
    if not _is_close(left, right, tol=abs(head) * 0.05):
        return False
    return True


def is_doji(data: list[dict]) -> bool:
    """Detect a doji candle."""
    if not data:
        return False
    row = data[-1]
    rng = row["h"] - row["l"]
    if rng == 0:
        return False
    body = abs(row["c"] - row["o"])
    return body <= rng * 0.1


def is_hammer(data: list[dict]) -> bool:
    """Detect a hammer candle."""
    if not data:
        return False
    row = data[-1]
    body = abs(row["c"] - row["o"])
    upper = row["h"] - max(row["o"], row["c"])
    lower = min(row["o"], row["c"]) - row["l"]
    if body == 0:
        body = (row["h"] - row["l"]) * 0.001
    return lower >= body * 2 and upper <= body


def is_bullish_engulfing(data: list[dict]) -> bool:
    if len(data) < 2:
        return False
    prev, curr = data[-2], data[-1]
    return (
        prev["c"] < prev["o"]
        and curr["c"] > curr["o"]
        and curr["o"] <= prev["c"]
        and curr["c"] >= prev["o"]
    )


def is_bearish_engulfing(data: list[dict]) -> bool:
    if len(data) < 2:
        return False
    prev, curr = data[-2], data[-1]
    return (
        prev["c"] > prev["o"]
        and curr["c"] < curr["o"]
        and curr["o"] >= prev["c"]
        and curr["c"] <= prev["o"]
    )


def is_morning_star(data: list[dict]) -> bool:
    if len(data) < 3:
        return False
    a, b, c = data[-3], data[-2], data[-1]
    body_a = abs(a["c"] - a["o"])
    body_b = abs(b["c"] - b["o"])
    return (
        a["c"] < a["o"]
        and body_b <= body_a * 0.5
        and c["c"] > c["o"]
        and c["c"] > a["o"] - body_a * 0.5
    )


def is_evening_star(data: list[dict]) -> bool:
    if len(data) < 3:
        return False
    a, b, c = data[-3], data[-2], data[-1]
    body_a = abs(a["c"] - a["o"])
    body_b = abs(b["c"] - b["o"])
    return (
        a["c"] > a["o"]
        and body_b <= body_a * 0.5
        and c["c"] < c["o"]
        and c["c"] < a["o"] + body_a * 0.5
    )

PATTERN_FUNCS = {
    "doji": is_doji,
    "hammer": is_hammer,
    "bullish_engulfing": is_bullish_engulfing,
    "bearish_engulfing": is_bearish_engulfing,
    "morning_star": is_morning_star,
    "evening_star": is_evening_star,
    "double_bottom": detect_double_bottom,
    "double_top": detect_double_top,
    "head_and_shoulders": detect_head_and_shoulders,
    "inverse_head_and_shoulders": detect_inverse_head_and_shoulders,
}

# Mapping of pattern name to directional bias
PATTERN_DIRECTION: dict[str, str] = {
    "double_top": "bearish",
    "double_bottom": "bullish",
    "head_and_shoulders": "bearish",
    "inverse_head_and_shoulders": "bullish",
    "bearish_engulfing": "bearish",
    "bullish_engulfing": "bullish",
    "evening_star": "bearish",
    "morning_star": "bullish",
    "hammer": "bullish",
    "doji": "neutral",
}


def scan_all(data: Iterable[Mapping], pattern_names: list[str] | None = None) -> str | None:
    rows = _as_list(data)
    names = pattern_names or list(PATTERN_FUNCS.keys())
    for name in names:
        func = PATTERN_FUNCS.get(name)
        if func and func(rows):
            return name
    return None


def scan(candles_dict: dict[str, list], pattern_names: list[str]) -> dict[str, str | None]:
    """Scan candle data for chart patterns per timeframe.

    Parameters
    ----------
    candles_dict : dict[str, list]
        Mapping of timeframe labels to candle lists.
    pattern_names : list[str]
        Names of patterns to check. If empty, all available patterns are tested.

    Returns
    -------
    dict[str, str | None]
        Detected pattern name for each timeframe, or ``None`` if no match.
    """

    results: dict[str, str | None] = {}
    for tf, candles in candles_dict.items():
        try:
            results[tf] = scan_all(candles, pattern_names)
        except Exception:
            results[tf] = None
    return results
