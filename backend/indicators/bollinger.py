

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
