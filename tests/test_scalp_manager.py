import importlib
import time
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
    sm._open_scalp_trades["t1"] = time.time() - sm.MAX_SCALP_HOLD_SECONDS - 1
    sm.monitor_scalp_positions()
    assert sm.order_mgr.closed == ["USD_JPY"]
