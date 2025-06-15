import os
import types
from datetime import datetime, timedelta, timezone

os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")

import execution.exit_manager as em


class DummyOM:
    def __init__(self):
        self.closed = []

    def close_position(self, instrument):
        self.closed.append(instrument)
        return {}

def test_check_max_hold(monkeypatch):
    now = datetime.now(timezone.utc)
    pos1 = {"instrument": "USD_JPY", "openTime": (now - timedelta(hours=7)).isoformat(), "unrealizedPL": "1"}
    pos2 = {"instrument": "EUR_USD", "openTime": (now - timedelta(hours=8)).isoformat(), "unrealizedPL": "-1"}
    monkeypatch.setattr(em, "get_open_positions", lambda: [pos1, pos2])
    dummy = DummyOM()
    monkeypatch.setattr(em, "OrderManager", lambda: dummy)
    monkeypatch.setenv("MAX_HOLD_HOURS", "6")
    em.check_max_hold()
    assert dummy.closed == ["USD_JPY", "EUR_USD"]


