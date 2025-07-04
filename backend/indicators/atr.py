from backend.utils import env_loader

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e
import numpy as np


def calculate_atr(high, low, close, period=None):
    """
    Calculate the Average True Range (ATR) for given price data.
    Args:
        high (pd.Series): High prices.
        low (pd.Series): Low prices.
        close (pd.Series): Close prices.
        period (int): Number of periods to use for ATR calculation.
    Returns:
        pd.Series: ATR values.
    """
    if period is None:
        period = int(env_loader.get_env('ATR_PERIOD', 14))
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr


def atr_tick_ratio(ticks, short_window=10):
    """Return ATR ratio of recent ticks versus overall average."""
    df = pd.DataFrame(ticks)
    if df.empty or not {"high", "low", "close"}.issubset(df.columns):
        return 0.0
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    if tr.empty:
        return 0.0
    recent_mean = tr.tail(short_window).mean()
    overall_mean = tr.mean()
    return float(recent_mean / overall_mean) if overall_mean else 0.0


__all__ = ["calculate_atr", "atr_tick_ratio"]
