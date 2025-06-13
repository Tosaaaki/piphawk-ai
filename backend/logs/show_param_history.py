import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# パラメータ変更履歴を格納した SQLite DB のパス
DB_PATH = Path(__file__).resolve().parent / "trades.db"


def fetch_history(param_name: str | None, since: str | None, until: str | None):
    """param_changes テーブルから履歴を取得する"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = (
            "SELECT timestamp, param_name, old_value, new_value, ai_reason "
            "FROM param_changes WHERE 1=1"
        )
        args: list[str] = []
        if param_name:
            query += " AND param_name = ?"
            args.append(param_name)
        if since:
            query += " AND timestamp >= ?"
            args.append(since)
        if until:
            query += " AND timestamp <= ?"
            args.append(until)
        query += " ORDER BY timestamp DESC"
        cursor.execute(query, args)
        return cursor.fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display parameter change history"
    )
    parser.add_argument("--param", help="Filter by parameter name")
    parser.add_argument("--days", type=int, help="Look back N days")
    parser.add_argument("--start", help="Start ISO timestamp (UTC)")
    parser.add_argument("--end", help="End ISO timestamp (UTC)")
    args = parser.parse_args()

    since: str | None = None
    until: str | None = None
    if args.days:
        since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    if args.start:
        since = args.start
    if args.end:
        until = args.end

    rows = fetch_history(args.param, since, until)
    if not rows:
        print("No records found.")
        return

    for ts, name, old, new, reason in rows:
        reason_str = f" - {reason}" if reason else ""
        print(f"{ts} | {name}: {old} -> {new}{reason_str}")


if __name__ == "__main__":
    main()
