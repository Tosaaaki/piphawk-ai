import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt

from backend.utils import env_loader

_BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", str(_BASE_DIR / "trades.db")))
ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")


def fetch_diffs(days: int = 1) -> list[float]:
    since = datetime.utcnow() - timedelta(days=days)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT instrument, close_price, tp_price, units, close_time
            FROM oanda_trades
            WHERE account_id = ? AND close_time IS NOT NULL AND tp_price IS NOT NULL AND close_time >= ?
            """,
            (ACCOUNT_ID, since.isoformat()),
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
