import numpy as np
import pandas as pd

from indicators.bollinger import multi_bollinger


def old_calc_single(prices, window=20, num_std=2.0):
    series = pd.Series(prices)
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    if ma.empty:
        return {"middle": 0.0, "upper": 0.0, "lower": 0.0}
    middle = ma.iloc[-1]
    sd = std.iloc[-1]
    return {"middle": middle, "upper": middle + num_std * sd, "lower": middle - num_std * sd}


def test_multi_bollinger_regression():
    data = {
        "A": np.linspace(1, 10, 10),
        "B": np.linspace(2, 11, 10),
    }
    expected = {tf: old_calc_single(p, window=3, num_std=1) for tf, p in data.items()}
    result = multi_bollinger(data, window=3, num_std=1)
    for tf in data:
        for key in ["middle", "upper", "lower"]:
            assert abs(expected[tf][key] - result[tf][key]) <= 1e-8
