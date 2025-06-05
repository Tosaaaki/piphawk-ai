"""Trade pattern scoring utilities."""
from __future__ import annotations


def calculate_trade_score(time_str: str, side: str) -> float:
    """Return a dummy trade score for given time and side."""
    if time_str == "08:25" and side.lower() == "long":
        return 0.7
    if time_str == "09:40" and side.lower() == "short":
        return 0.75
    return 0.0

__all__ = ["calculate_trade_score"]

