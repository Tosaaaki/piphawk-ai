import os
import pandas as pd
import numpy as np

def calculate_rsi(prices, period: int = None):
    """
    Calculate the Relative Strength Index (RSI) for a given price series.

    Args:
        prices (list or pd.Series): Price data (e.g. closing prices).
        period (int): Number of periods to use for RSI calculation.

    Returns:
        pd.Series: RSI values.
    """
    if period is None:
        period = int(os.getenv('RSI_PERIOD', 14))
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(window=period, min_periods=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi