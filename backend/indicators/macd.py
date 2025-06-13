try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations.",
        " Install it with 'pip install pandas'."
    ) from e
from typing import Iterable, Tuple

from backend.utils import env_loader


def calculate_macd(
    prices: Iterable[float],
    *,
    fast_period: int | None = None,
    slow_period: int | None = None,
    signal_period: int | None = None,
) -> Tuple[pd.Series, pd.Series]:
    """Return MACD line and signal line."""
    if fast_period is None:
        fast_period = int(env_loader.get_env("MACD_FAST_PERIOD", 12))
    if slow_period is None:
        slow_period = int(env_loader.get_env("MACD_SLOW_PERIOD", 26))
    if signal_period is None:
        signal_period = int(env_loader.get_env("MACD_SIGNAL_PERIOD", 9))

    series = pd.Series(prices, dtype="float64")
    ema_fast = series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = series.ewm(span=slow_period, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal


def calculate_macd_histogram(
    prices: Iterable[float],
    *,
    fast_period: int | None = None,
    slow_period: int | None = None,
    signal_period: int | None = None,
) -> pd.Series:
    """Return MACD histogram."""
    macd, signal = calculate_macd(
        prices,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
    )
    return macd - signal
