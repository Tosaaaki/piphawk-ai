import importlib
import os
import sqlite3
import tempfile

import pytest


def test_sync_exits_updates_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    os.environ["TRADES_DB_PATH"] = tmp.name

    import backend.logs.log_manager as lm
    import backend.logs.reconcile_trades as rt
    import execution.sync_manager as sm

    importlib.reload(lm)
    importlib.reload(rt)
    importlib.reload(sm)

    monkeypatch.setattr(sm, "update_oanda_trades", lambda: None)

    lm.init_db()
    conn = lm.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trades (instrument, entry_time, entry_price, units) VALUES (?,?,?,?)",
        ("EUR_USD", "2024-01-01T00:00:00Z", 1.0, 1000),
    )
    cur.execute(
        """
        INSERT INTO oanda_trades (
            trade_id, account_id, instrument, open_time, close_time,
            open_price, close_price, units, realized_pl, state, tp_price, sl_price
        ) VALUES (1, 'abc', 'EUR_USD', '2024-01-01T00:00:05Z',
                   '2024-01-01T01:00:00Z', 1.0, 1.1, 1000, 1.5, 'CLOSED', NULL, NULL)
        """,
    )
    conn.commit()
    conn.close()

    sm.sync_exits()

    conn = lm.get_db_connection()
    row = conn.execute(
        "SELECT exit_time, exit_price, profit_loss FROM trades WHERE trade_id = 1"
    ).fetchone()
    conn.close()

    os.unlink(tmp.name)
    os.environ.pop("TRADES_DB_PATH", None)

    assert row[0] == "2024-01-01T01:00:00Z"
    assert abs(row[1] - 1.1) < 1e-8
    assert abs(row[2] - 1.5) < 1e-8

