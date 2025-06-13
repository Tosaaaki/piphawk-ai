import pytest

from strategies.trend_strategy import TrendStrategy


def test_trend_strategy_breakout_long():
    strat = TrendStrategy()
    context = {
        "closes": [1.0, 1.05, 1.06, 1.07, 1.1],
        "highs": [1.01, 1.06, 1.05, 1.06, 1.09],
        "lows": [0.99, 1.03, 1.04, 1.05, 1.07],
        "ema_fast_h1": 1.0,
        "ema_slope_h1": 0.1,
    }
    assert strat.decide_entry(context) == "long"


def test_trend_strategy_breakout_short():
    strat = TrendStrategy()
    context = {
        "closes": [1.2, 1.15, 1.14, 1.13, 1.1],
        "highs": [1.21, 1.2, 1.19, 1.18, 1.17],
        "lows": [1.19, 1.16, 1.15, 1.14, 1.12],
        "ema_fast_h1": 1.2,
        "ema_slope_h1": -0.1,
    }
    assert strat.decide_entry(context) == "short"
