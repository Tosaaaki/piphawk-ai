from __future__ import annotations

"""Simple SQLite helper utilities."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from backend.utils import env_loader

# Default DB path is repository root / trades.db unless TRADES_DB_PATH env var is set
_BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = env_loader.get_env("TRADES_DB_PATH", str(_BASE_DIR / "trades.db"))


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new SQLite connection using the configured database path."""
    return sqlite3.connect(db_path or DB_PATH)


@contextmanager
def connect(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager wrapper for :func:`sqlite3.connect`."""
    conn = sqlite3.connect(db_path or DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
