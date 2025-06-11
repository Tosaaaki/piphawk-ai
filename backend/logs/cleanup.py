from __future__ import annotations
from backend.utils import env_loader
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from backend.logs.log_manager import DB_PATH

LOG_PATH = Path(__file__).resolve().parent / "exit_log.jsonl"
DAYS = int(env_loader.get_env("DAYS", "30"))

# データベースをVACUUMして不要領域を解放する

def vacuum_db() -> None:
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("VACUUM")
        print(f"vacuumed {DB_PATH}")
    else:
        print(f"{DB_PATH} not found")

# 指定日数より古いExitログを削除する

def prune_exit_log(days: int = DAYS) -> None:
    if not LOG_PATH.exists():
        print(f"{LOG_PATH} not found")
        return
    cutoff = datetime.utcnow() - timedelta(days=days)
    new_lines: list[str] = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                ts = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                if ts >= cutoff:
                    new_lines.append(line)
            except Exception:
                # 日付が解析できない行は破棄
                pass
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"pruned {LOG_PATH} to {days} days")


def main() -> None:
    vacuum_db()
    prune_exit_log(DAYS)


if __name__ == "__main__":
    main()
