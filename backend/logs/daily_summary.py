import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt

DB_PATH = Path(__file__).resolve().parent / "trades.db"


def fetch_diffs(days: int = 1) -> list[float]:
    since = datetime.utcnow() - timedelta(days=days)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT instrument, close_price, tp_price, units, close_time
            FROM oanda_trades
            WHERE close_time IS NOT NULL AND tp_price IS NOT NULL AND close_time >= ?
            """,
            (since.isoformat(),),
        )
        rows = cursor.fetchall()
    diffs: list[float] = []
    for instrument, close_price, tp_price, units, _ in rows:
        if close_price is None or tp_price is None:
            continue
        pip = 0.01 if instrument.endswith("JPY") else 0.0001
        if units > 0:
            diff = (tp_price - close_price) / pip
        else:
            diff = (close_price - tp_price) / pip
        diffs.append(diff)
    return diffs


def main() -> None:
    diffs = fetch_diffs(1)
    if not diffs:
        print("No closed trades found for the period.")
        return
    plt.hist(diffs, bins=20)
    plt.xlabel("pips short of TP")
    plt.ylabel("count")
    out = Path(__file__).resolve().parent / "tp_distance_hist.png"
    plt.savefig(out)
    print(f"Histogram saved to {out}")


if __name__ == "__main__":
    main()
