"""フィルター効果を集計する簡易スクリプト."""
from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from backend.utils import env_loader

DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", "trades.db"))


def summarize(db_path: Path = DB_PATH) -> dict:
    """entry_skips と trades を読み込みフィルター発生回数を返す."""
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT reason FROM entry_skips")
        reasons = [r[0] for r in c.fetchall()]
        c.execute("SELECT COUNT(*) FROM trades")
        trade_total = c.fetchone()[0] or 0
    counts = Counter(reasons)
    return {
        reason: {
            "count": cnt,
            "ratio": cnt / trade_total if trade_total else 0.0,
        }
        for reason, cnt in counts.items()
    }


def print_summary(stats: dict) -> None:
    """集計結果を見やすく表示する."""
    print("Filter Statistics")
    print("-----------------")
    for reason, data in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
        pct = data["ratio"] * 100
        print(f"{reason}: {data['count']} ({pct:.1f}% vs trades)")


if __name__ == "__main__":
    summary = summarize()
    print_summary(summary)

__all__ = ["summarize", "print_summary"]
