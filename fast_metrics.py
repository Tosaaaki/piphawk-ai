from __future__ import annotations

"""軽量な指標計算モジュール."""

from typing import Tuple

from core.ring_buffer import RingBuffer


def calc_mid_spread(buffer: RingBuffer, window: int = 1) -> Tuple[float, float]:
    """ミッド価格とスプレッドを計算する."""
    items = buffer.latest(window)
    if not items:
        return 0.0, 0.0
    bids = [float(t["bid"]) for t in items]
    asks = [float(t["ask"]) for t in items]
    mid = (sum(bids) + sum(asks)) / (2 * len(items))
    spread = sum(a - b for a, b in zip(asks, bids)) / len(items)
    return mid, spread
