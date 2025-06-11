import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "diagnostics.db"


def _ensure_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            decision_type TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            metrics TEXT
        )
        """
    )
    conn.commit()


def log(decision_type: str, ai_response: str, metrics: dict | None = None) -> None:
    """Store AI response and metrics into diagnostics.db."""
    with sqlite3.connect(DB_PATH) as conn:
        _ensure_db(conn)
        conn.execute(
            "INSERT INTO diagnostics (timestamp, decision_type, ai_response, metrics) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                decision_type,
                ai_response,
                json.dumps(metrics or {}, ensure_ascii=False),
            ),
        )
        conn.commit()


def fetch_all(limit: int | None = None) -> list[tuple]:
    """Return rows from diagnostics table."""
    with sqlite3.connect(DB_PATH) as conn:
        _ensure_db(conn)
        cur = conn.cursor()
        q = "SELECT timestamp, decision_type, ai_response, metrics FROM diagnostics ORDER BY id DESC"
        if limit:
            q += f" LIMIT {int(limit)}"
        cur.execute(q)
        return cur.fetchall()


__all__ = ["log", "fetch_all"]
