

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e
import numpy as np
import os

def calculate_bollinger_bands(prices, window=None, num_std=None):
    """
    Calculate Bollinger Bands for a given price series.
    
    Args:
        prices (pd.Series or list-like): Series of prices (e.g., closing prices).
        window (int): The lookback period for the moving average (default 20 or from env BOLLINGER_WINDOW).
        num_std (float): Number of standard deviations for the bands (default 2 or from env BOLLINGER_STD).
    
    Returns:
        pd.DataFrame: DataFrame with columns ['middle_band', 'upper_band', 'lower_band']
    """
    # Read window and num_std from environment variables if not provided
    if window is None:
        window = int(os.environ.get("BOLLINGER_WINDOW", 20))
    if num_std is None:
        try:
            num_std = float(os.environ.get("BOLLINGER_STD", 2))
        except ValueError:
            num_std = 2
    prices = pd.Series(prices)
    middle_band = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    upper_band = middle_band + (num_std * rolling_std)
    lower_band = middle_band - (num_std * rolling_std)
    return pd.DataFrame({
        'middle_band': middle_band,
        'upper_band': upper_band,
        'lower_band': lower_band
    })


def calculate_bb_width(prices, window=None, num_std=None):
    """Return Bollinger Band width as a Series."""
    df = calculate_bollinger_bands(prices, window=window, num_std=num_std)
    return df['upper_band'] - df['lower_band']


def close_breaks_bbands(price_series, level, window=20):
    """Return ``True`` if close price breaks the Bollinger band."""
    series = pd.Series(price_series)
    if len(series) < 2:
        return False
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    if ma.isna().iloc[-1] or ma.isna().iloc[-2]:
        return False
    prev_close, last_close = series.iloc[-2], series.iloc[-1]
    prev_upper = ma.iloc[-2] + level * std.iloc[-2]
    prev_lower = ma.iloc[-2] - level * std.iloc[-2]
    last_upper = ma.iloc[-1] + level * std.iloc[-1]
    last_lower = ma.iloc[-1] - level * std.iloc[-1]
    prev_out = prev_close > prev_upper or prev_close < prev_lower
    last_out = last_close > last_upper or last_close < last_lower
    return last_out and not prev_out


def high_hits_bbands(price_series, level, window=20):
    """Return ``True`` if high or low touches the Bollinger band."""
    df = pd.DataFrame(price_series)
    if df.empty or not {"high", "low", "close"}.issubset(df.columns):
        return False
    close = df["close"]
    ma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    if ma.isna().iloc[-1]:
        return False
    upper = ma.iloc[-1] + level * std.iloc[-1]
    lower = ma.iloc[-1] - level * std.iloc[-1]
    high_val = float(df["high"].iloc[-1])
    low_val = float(df["low"].iloc[-1])
    return high_val >= upper or low_val <= lower


__all__ = [
    "calculate_bollinger_bands",
    "calculate_bb_width",
    "close_breaks_bbands",
    "high_hits_bbands",
]
