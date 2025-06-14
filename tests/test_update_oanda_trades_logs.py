import logging
import types

from backend.logs import update_oanda_trades as uot


class DummyConn:
    total_changes = 0

    def cursor(self):
        class DummyCursor:
            def execute(self, *a, **k):
                pass

        return DummyCursor()

    def commit(self):
        pass

    def close(self):
        pass


def _setup_monkeypatch(monkeypatch, transactions):
    monkeypatch.setattr(uot, "fetch_transactions", lambda *a, **k: {"transactions": transactions})
    monkeypatch.setattr(uot, "get_last_transaction_id", lambda: "0")
    monkeypatch.setattr(uot, "set_last_transaction_id", lambda x: None)
    monkeypatch.setattr(uot, "log_oanda_trade", lambda *a, **kw: None)
    monkeypatch.setattr(uot, "log_error", lambda *a, **kw: None)
    monkeypatch.setattr(uot, "init_db", lambda: None)
    monkeypatch.setattr(uot, "get_db_connection", lambda: DummyConn())
    labels: list[tuple[str, str]] = []
    monkeypatch.setattr(uot, "add_trade_label", lambda tid, label: labels.append((tid, label)))
    return labels


def test_reject_reason_logging(monkeypatch, caplog):
    txs = [
        {
            "id": "1",
            "type": "STOP_LOSS_ORDER_REJECT",
            "rejectReason": "TRADE_DOESNT_EXIST",
            "time": "2023-01-01T00:00:00Z",
        },
        {
            "id": "2",
            "type": "STOP_LOSS_ORDER_REJECT",
            "rejectReason": "INVALID_PRICE",
            "time": "2023-01-01T00:01:00Z",
        },
    ]

    _setup_monkeypatch(monkeypatch, txs)

    caplog.set_level(logging.INFO)
    uot.update_oanda_trades()

    assert any(
        r.levelno == logging.INFO and "TRADE_DOESNT_EXIST" in r.getMessage() for r in caplog.records
    )
    assert not any(
        r.levelno == logging.WARNING and "TRADE_DOESNT_EXIST" in r.getMessage() for r in caplog.records
    )
    assert any(
        r.levelno == logging.WARNING and "INVALID_PRICE" in r.getMessage() for r in caplog.records
    )


def test_trade_labels_logged(monkeypatch):
    txs = [
        {
            "id": "1",
            "type": "ORDER_FILL",
            "instrument": "EUR_USD",
            "units": "1",
            "price": "1.0",
            "pl": "0.0",
            "time": "2023-01-01T00:00:00Z",
        },
        {
            "id": "2",
            "type": "TAKE_PROFIT_ORDER",
            "tradeID": "1",
            "price": "1.1",
            "time": "2023-01-01T01:00:00Z",
            "tradesClosed": [{"tradeID": "1", "realizedPL": "0.1"}],
        },
    ]

    labels = _setup_monkeypatch(monkeypatch, txs)
    uot.update_oanda_trades()

    assert ("1", "FILL") in labels
    assert ("1", "TP") in labels
