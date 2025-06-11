import importlib
import time
import sys
from types import SimpleNamespace

import os
os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")
import execution.scalp_manager as sm

class DummyOM:
    def __init__(self):
        self.closed = []
        self.placed = []

    def place_market_order(self, instrument, units, comment_json=None):
        self.placed.append((instrument, units))
        return {"lastTransactionID": "t1", "orderFillTransaction": {"price": "1"}}

    def adjust_tp_sl(self, *a, **k):
        return None

    def close_position(self, instrument, side="both"):
        self.closed.append(instrument)
        return {"ok": True}


def test_auto_exit_on_timeout(monkeypatch):
    importlib.reload(sm)
    monkeypatch.setattr(sm, "OrderManager", lambda: DummyOM())
    sm.order_mgr = sm.OrderManager()
    monkeypatch.setattr(sm, "get_open_positions", lambda: [{"instrument": "USD_JPY", "id": "t1"}])
    monkeypatch.setattr(sm, "get_dynamic_hold_seconds", lambda _i: 1)
    sm._open_scalp_trades["t1"] = time.time() - 2
    sm.monitor_scalp_positions()
    assert sm.order_mgr.closed == ["USD_JPY"]


class FakeSeries:
    def __init__(self, val):
        class _IL:
            def __getitem__(self, idx):
                return val

        self.iloc = _IL()
        self._val = val

    def __getitem__(self, idx):
        return self._val


def test_hold_seconds_varies_with_atr(monkeypatch):
    importlib.reload(sm)
    monkeypatch.setattr(sm, "OrderManager", lambda: DummyOM())
    sm.order_mgr = sm.OrderManager()

    candle = {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True}
    fetch_mod = SimpleNamespace(fetch_candles=lambda *a, **k: [candle] * 20)
    sys.modules["backend.market_data.candle_fetcher"] = fetch_mod

    atr_mod_small = SimpleNamespace(calculate_atr=lambda *a, **k: FakeSeries(0.001))
    sys.modules["backend.indicators.atr"] = atr_mod_small

    monkeypatch.setenv("HOLD_TIME_MIN", "1")
    monkeypatch.setenv("HOLD_TIME_MAX", "5000")
    hold_small = sm.get_dynamic_hold_seconds("EUR_USD")

    atr_mod_big = SimpleNamespace(calculate_atr=lambda *a, **k: FakeSeries(0.01))
    sys.modules["backend.indicators.atr"] = atr_mod_big
    hold_big = sm.get_dynamic_hold_seconds("EUR_USD")

    assert hold_big > hold_small
