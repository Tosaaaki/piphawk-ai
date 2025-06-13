import importlib
import sqlite3

from fastapi.testclient import TestClient

from backend.api import main


def setup_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE oanda_trades (
            trade_id INTEGER PRIMARY KEY,
            account_id TEXT,
            instrument TEXT,
            open_time TEXT,
            close_time TEXT,
            open_price REAL,
            close_price REAL,
            units INTEGER,
            realized_pl REAL,
            unrealized_pl REAL,
            state TEXT,
            tp_price REAL,
            sl_price REAL
        )
        """
    )
    cur.execute(
        "INSERT INTO oanda_trades VALUES (1, 'test', 'USD_JPY', 't1', 't2', 1.0, 1.1, 100, 5.0, 0.0, 'CLOSED', 0, 0)"
    )
    conn.commit()
    conn.close()


def test_get_recent_trades(monkeypatch, tmp_path):
    db = tmp_path / "t.db"
    setup_db(db)
    monkeypatch.setenv("TRADES_DB_PATH", str(db))
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "test")
    # disable scheduler job registration
    monkeypatch.setattr(main, "schedule_hourly_summary_job", lambda: None)
    importlib.reload(main)
    client = TestClient(main.app)
    resp = client.get("/trades/recent?limit=1")
    assert resp.status_code == 200
    assert resp.json()["trades"][0]["trade_id"] == 1
