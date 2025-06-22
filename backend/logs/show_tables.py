import sqlite3
from pathlib import Path

from backend.utils import db_helper, env_loader

# DBのパスを取得
_BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", db_helper.DB_PATH))

def list_tables():
    """Return list of table names."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cur.fetchall()]

def show_schema(table: str):
    """Return column information for a table."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return cur.fetchall()

def main() -> None:
    tables = list_tables()
    if not tables:
        print("No tables found")
        return
    print("Tables:")
    for t in tables:
        print(f" - {t}")
    for t in tables:
        print(f"\n-- {t} --")
        for _, name, col_type, *_ in show_schema(t):
            print(f"{name}: {col_type}")

if __name__ == "__main__":
    main()
