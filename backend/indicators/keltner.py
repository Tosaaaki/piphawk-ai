"""Simple Keltner Channel implementation."""

from __future__ import annotations

from typing import Sequence, Dict, List
from backend.utils import env_loader


def calculate_keltner_bands(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    window: int | None = None,
    atr_mult: float | None = None,
) -> Dict[str, List[float]]:
    """Return Keltner Channel bands.

    Parameters
    ----------
    high, low, close : sequence of float
        価格系列。
    window : int, optional
        EMA/ATR の期間。環境変数 ``KELTNER_WINDOW`` をデフォルト値とする。
    atr_mult : float, optional
        ATR 乗数。環境変数 ``KELTNER_ATR_MULT`` をデフォルト値とする。
    """
    if window is None:
        window = int(env_loader.get_env("KELTNER_WINDOW", 20))
    if atr_mult is None:
        atr_mult = float(env_loader.get_env("KELTNER_ATR_MULT", 1.5))
    highs = list(map(float, high))
    lows = list(map(float, low))
    closes = list(map(float, close))
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    ema: List[float] = []
    alpha = 2 / (window + 1)
    prev = None
    for tp in typical_prices:
        prev = tp if prev is None else prev + alpha * (tp - prev)
        ema.append(prev)
    bands_upper: List[float] = []
    bands_lower: List[float] = []
    tr_values: List[float] = []
    prev_close = None
    for i, (h, l, c) in enumerate(zip(highs, lows, closes)):
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        tr_values.append(tr)
        if len(tr_values) > window:
            tr_values.pop(0)
        atr = sum(tr_values) / len(tr_values)
        bands_upper.append(ema[i] + atr_mult * atr)
        bands_lower.append(ema[i] - atr_mult * atr)
        prev_close = c
    return {
        "middle_band": ema,
        "upper_band": bands_upper,
        "lower_band": bands_lower,
    }


__all__ = ["calculate_keltner_bands"]
