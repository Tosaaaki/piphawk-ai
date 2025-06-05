import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from backend.logs.log_manager import get_db_connection, init_db
from backend.utils import env_loader

logger = logging.getLogger(__name__)

MATCH_SEC = int(env_loader.get_env("OANDA_MATCH_SEC", "60"))


def _iso_to_dt(ts: str) -> datetime:
    """Convert ISO string to aware UTC datetime."""
    if ts.endswith("Z"):
        ts = ts[:-1]
    return datetime.fromisoformat(ts)


def reconcile_trades() -> None:
    """Update local trades with realized P/L from OANDA history."""
    init_db()
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            "SELECT trade_id, instrument, entry_time, units FROM trades"
        )
        local_trades = cur.fetchall()

        for lt in local_trades:
            if lt["units"] == 0:
                continue
            entry_time = _iso_to_dt(lt["entry_time"])
            start = (entry_time - timedelta(seconds=MATCH_SEC)).isoformat()
            end = (entry_time + timedelta(seconds=MATCH_SEC)).isoformat()
            cur.execute(
                """
                SELECT trade_id, close_time, close_price, realized_pl,
                       ABS(strftime('%s', open_time) - strftime('%s', ?)) AS diff
                FROM oanda_trades
                WHERE instrument = ? AND close_time IS NOT NULL
                  AND open_time BETWEEN ? AND ?
                ORDER BY diff ASC
                LIMIT 1
                """,
                (lt["entry_time"], lt["instrument"], start, end),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE trades
                    SET profit_loss = ?, exit_time = ?, exit_price = ?
                    WHERE trade_id = ?
                    """,
                    (
                        row["realized_pl"],
                        row["close_time"],
                        row["close_price"],
                        lt["trade_id"],
                    ),
                )
                logger.info(
                    "Reconciled trade %s with OANDA trade %s",
                    lt["trade_id"],
                    row["trade_id"],
                )
            else:
                logger.warning(
                    "No OANDA match found for trade_id %s", lt["trade_id"]
                )
        conn.commit()


if __name__ == "__main__":
    reconcile_trades()
