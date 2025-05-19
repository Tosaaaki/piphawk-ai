import os
import pandas as pd
from typing import List, Union

def calculate_ema(
    prices: Union[List[float], pd.Series],
    period: int = None
) -> pd.Series:
    """
    Calculate the Exponential Moving Average (EMA) for a given list or Series of prices.

    Args:
        prices (List[float] or pd.Series): List or Series of price data.
        period (int, optional): The period over which to calculate the EMA. If not provided,
            reads from the EMA_PERIOD environment variable, or defaults to 20.

    Returns:
        pd.Series: EMA values.
    """
    if period is None:
        period_env = os.getenv("EMA_PERIOD")
        try:
            period = int(period_env) if period_env is not None else 20
        except ValueError:
            period = 20
    prices_series = pd.Series(prices)
    ema = prices_series.ewm(span=period, adjust=False).mean()
    return ema
