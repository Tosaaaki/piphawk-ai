"""Archive old tick data once per week."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from backend.utils import db_helper, env_loader

DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", db_helper.DB_PATH))


def archive_old_ticks(days: int = 30) -> int:
    """Move tick records older than ``days`` to ``ticks_archive`` table."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # テーブルが存在しない場合は何もしない
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ticks'"
        )
        if cur.fetchone() is None:
            return 0
        cur.execute(
            "CREATE TABLE IF NOT EXISTS ticks_archive AS SELECT * FROM ticks WHERE 0"
        )
        cur.execute(
            "SELECT COUNT(*) FROM ticks WHERE timestamp < ?",
            (cutoff.isoformat(),),
        )
        count = cur.fetchone()[0]
        if count:
            cur.execute(
                "INSERT INTO ticks_archive SELECT * FROM ticks WHERE timestamp < ?",
                (cutoff.isoformat(),),
            )
            cur.execute(
                "DELETE FROM ticks WHERE timestamp < ?",
                (cutoff.isoformat(),),
            )
            conn.commit()
            conn.execute("VACUUM")
    return count


if __name__ == "__main__":
    num = archive_old_ticks()
    print(f"archived {num} ticks")
