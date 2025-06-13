try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e
from typing import List, Union

from backend.utils import env_loader


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
        period_env = env_loader.get_env("EMA_PERIOD")
        try:
            period = int(period_env) if period_env is not None else 20
        except ValueError:
            period = 20
    prices_series = pd.Series(prices)
    ema = prices_series.ewm(span=period, adjust=False).mean()
    return ema


def get_ema_gradient(series: Union[List[float], pd.Series], *, pip_size: float = 0.01) -> str:
    """Return the latest EMA gradient as ``"up"``, ``"down"`` or ``"flat"``.

    Parameters
    ----------
    series : list or pandas.Series
        EMA series ordered oldest → newest.
    pip_size : float, default 0.01
        Threshold used to judge a "flat" slope.

    Returns
    -------
    str
        ``"up"`` | ``"down"`` | ``"flat"``
    """

    try:
        if hasattr(series, "iloc"):
            if len(series) < 2:
                return "flat"
            latest = float(series.iloc[-1])
            prev = float(series.iloc[-2])
        else:
            if len(series) < 2:
                return "flat"
            latest = float(series[-1])
            prev = float(series[-2])
    except Exception:
        return "flat"

    diff = latest - prev
    if diff > pip_size * 0.05:
        return "up"
    if diff < -pip_size * 0.05:
        return "down"
    return "flat"
