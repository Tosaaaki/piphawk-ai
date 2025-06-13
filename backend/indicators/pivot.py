from typing import Dict, Sequence


def calculate_pivots(high: float, low: float, close: float) -> Dict[str, float]:
    """Return classic floor-trader pivot levels."""
    pivot = (high + low + close) / 3.0
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    return {"pivot": pivot, "r1": r1, "s1": s1, "r2": r2, "s2": s2}
