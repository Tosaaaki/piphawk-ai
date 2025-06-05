from collections import deque
from typing import Sequence, Tuple


def _compute_vwap(prices: Sequence[float], volumes: Sequence[float]) -> float:
    """Return VWAP for given price and volume series."""
    total_vol = sum(float(v) for v in volumes)
    if total_vol == 0:
        return 0.0
    return sum(float(p) * float(v) for p, v in zip(prices, volumes)) / total_vol


deviation_history: deque[float] = deque(maxlen=20)


def get_vwap_delta(prices: Sequence[float], volumes: Sequence[float]) -> Tuple[float, float]:
    """Return current VWAP deviation and shrinkage ratio."""
    if len(prices) != len(volumes) or not prices:
        return 0.0, 0.0
    vwap = _compute_vwap(prices, volumes)
    cur_price = float(prices[-1])
    deviation = cur_price - vwap
    deviation_history.append(deviation)
    avg_dev = sum(abs(d) for d in deviation_history) / len(deviation_history)
    shrink = deviation / avg_dev if avg_dev else 0.0
    return deviation, shrink


__all__ = ["get_vwap_delta"]
