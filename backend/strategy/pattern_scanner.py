import math
from typing import Iterable, Mapping

CANDLE_KEYS = ('o', 'h', 'l', 'c')

def _as_list(data: Iterable[Mapping]) -> list[dict]:
    return [
        {k: float(row.get(k, 0)) for k in CANDLE_KEYS}
        for row in data
    ]

def _is_close(a: float, b: float, tol: float = 0.001) -> bool:
    return abs(a - b) <= tol

def detect_double_bottom(data: list[dict]) -> bool:
    if len(data) < 4:
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
    if len(data) < 4:
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

def scan_all(data: Iterable[Mapping]) -> str | None:
    rows = _as_list(data)
    if detect_double_bottom(rows):
        return "double_bottom"
    if detect_double_top(rows):
        return "double_top"
    return None