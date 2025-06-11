import importlib
import time
import sys
from types import SimpleNamespace

import os
import pandas as pd

os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")

import execution.scalp_manager as sm


class DummyOM:
    def __init__(self):
        self.closed = []

    def close_position(self, instrument, side="both"):
        self.closed.append(instrument)
        return {"ok": True}


def test_exit_on_momentum_loss(monkeypatch):
    importlib.reload(sm)
    monkeypatch.setattr(sm, "OrderManager", lambda: DummyOM())
    sm.order_mgr = sm.OrderManager()
    monkeypatch.setattr(
        sm,
        "get_open_positions",
        lambda: [{"instrument": "USD_JPY", "id": "t1"}],
    )
    sm._open_scalp_trades["t1"] = time.time()

    fetch_mod = SimpleNamespace(fetch_candles=lambda *a, **k: [{}] * 30)
    indicators = {
        "ema_fast": pd.Series([1.0, 0.99]),
        "ema_slow": pd.Series([1.0, 0.995]),
        "rsi": pd.Series([49.0]),
        "macd_hist": pd.Series([-0.1]),
    }
    ind_mod = SimpleNamespace(calculate_indicators=lambda *a, **k: indicators)
    sys.modules["backend.market_data.candle_fetcher"] = fetch_mod
    sys.modules["backend.indicators.calculate_indicators"] = ind_mod
    monkeypatch.setenv("PIP_SIZE", "0.01")

    sm.monitor_scalp_positions()
    assert sm.order_mgr.closed == ["USD_JPY"]
