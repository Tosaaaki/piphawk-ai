import pytest

from indicators.bollinger import multi_bollinger
from signals.scalp_strategy import analyze_environment_m1, should_enter_trade_s10


def test_multi_bollinger_basic():
    data = {
        "M1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "M5": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    }
    res = multi_bollinger(data, window=3, num_std=1)
    assert set(res.keys()) == {"M1", "M5"}
    for v in res.values():
        assert set(v.keys()) == {"middle", "upper", "lower"}


def test_analyze_environment_m1():
    prices = [1] * 10 + [2] * 10
    mode = analyze_environment_m1(prices)
    assert mode in {"trend", "range"}


def test_should_enter_trade_s10_trend_breakout():
    bands = {"upper": 1.5, "lower": 0.5}
    side = should_enter_trade_s10("trend", [1.6], bands)
    assert side == "long"


