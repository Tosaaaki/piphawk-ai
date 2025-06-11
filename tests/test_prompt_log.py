import os
import sqlite3
from pathlib import Path

from backend.logs.log_manager import init_db, log_prompt_response


def test_log_prompt_response(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["TRADES_DB_PATH"] = str(db_path)
    init_db()
    log_prompt_response("ENTRY", "USD_JPY", "test prompt", "test response")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT decision_type, instrument, prompt, response FROM prompt_logs"
    )
    row = cur.fetchone()
    conn.close()
    assert row == ("ENTRY", "USD_JPY", "test prompt", "test response")
