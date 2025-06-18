import os

from filters.market_filters import is_tradeable


def test_is_tradeable_basic(monkeypatch):
    monkeypatch.setenv("TRADE_START_H", "0")
    monkeypatch.setenv("TRADE_END_H", "24")
    monkeypatch.setenv("MAX_SPREAD_PIPS", "2")
    monkeypatch.setenv("MIN_ATR_PIPS", "2")
    assert is_tradeable("USD_JPY", "M1", 0.01, 0.03)
    assert not is_tradeable("USD_JPY", "M1", 0.03, 0.03)
    assert not is_tradeable("USD_JPY", "M1", 0.01, 0.01)
