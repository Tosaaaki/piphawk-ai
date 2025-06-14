import importlib
from types import SimpleNamespace

import backend.logs.trade_logger as tl


def test_entry_and_exit_labels(monkeypatch):
    recorded = []
    monkeypatch.setattr(tl, "_log_trade", lambda **kw: 1)
    monkeypatch.setattr(tl, "add_trade_label", lambda tid, label: recorded.append((tid, label)))

    tl.log_trade(
        instrument="EUR_USD",
        entry_time="2024-01-01T00:00:00",
        entry_price=1.0,
        units=1,
        ai_reason="test",
    )
    tl.log_trade(
        instrument="EUR_USD",
        entry_time="2024-01-01T00:00:00",
        entry_price=1.0,
        units=1,
        ai_reason="test",
        exit_time="2024-01-01T01:00:00",
        exit_price=1.1,
        exit_reason=tl.ExitReason.AI,
    )

    assert recorded[0] == (1, "ENTRY")
    assert recorded[1] == (1, "EXIT")
