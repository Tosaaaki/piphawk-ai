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


def test_in_trade_hours_decimal(monkeypatch):
    from datetime import datetime, timezone

    from filters.market_filters import _in_trade_hours

    monkeypatch.setenv("TRADE_START_H", "7")
    monkeypatch.setenv("TRADE_END_H", "3.5")

    ts_trade = datetime(2023, 1, 1, 23, 0, tzinfo=timezone.utc)
    assert _in_trade_hours(ts_trade)

    ts_block = datetime(2023, 1, 1, 18, 40, tzinfo=timezone.utc)
    assert not _in_trade_hours(ts_block)


def test_in_trade_hours_default(monkeypatch):
    from datetime import datetime, timezone

    from filters.market_filters import _in_trade_hours

    monkeypatch.setenv("TRADE_START_H", "7")
    monkeypatch.setenv("TRADE_END_H", "23")

    ts = datetime(2023, 1, 1, 4, 0, tzinfo=timezone.utc)
    assert _in_trade_hours(ts)
