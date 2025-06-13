import pytest
import pandas as pd

from backend.indicators.bollinger import close_breaks_bbands, high_hits_bbands
from backend.indicators.atr import atr_tick_ratio


def test_close_breaks_bbands():
    prices = [1.0] * 21 + [1.5]
    assert close_breaks_bbands(prices, 1)


def test_high_hits_bbands():
    data = [{"high": 1.0, "low": 1.0, "close": 1.0}] * 20
    data.append({"high": 1.5, "low": 0.8, "close": 1.0})
    assert high_hits_bbands(data, 1)


def test_atr_tick_ratio():
    ticks = [{"high": 1.01, "low": 0.99, "close": 1.0}] * 15
    ratio1 = atr_tick_ratio(ticks)
    assert ratio1 == pytest.approx(1.0)
    ticks.extend([{"high": 1.05, "low": 0.95, "close": 1.0}] * 5)
    ratio2 = atr_tick_ratio(ticks)
    assert ratio2 > 1.0
