import os
from typing import Sequence

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e


def calculate_polarity(prices: Sequence[float], *, period: int = None) -> pd.Series:
    """Return rolling polarity score between -1 and 1."""
    if period is None:
        period = int(os.getenv("POLARITY_PERIOD", "10"))
    series = pd.Series(prices)
    diff = series.diff()

    def _sign(val: float) -> int:
        if val > 0:
            return 1
        if val < 0:
            return -1
        return 0

    sign_series = diff.apply(_sign)
    polarity = sign_series.rolling(window=period, min_periods=1).sum() / period
    return polarity
