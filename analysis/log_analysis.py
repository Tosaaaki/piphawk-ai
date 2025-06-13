from __future__ import annotations

"""Utility functions for log analysis."""

from typing import Dict

from backend.logs.log_manager import get_db_connection


def label_win_rates() -> Dict[str, float]:
    """Return win rate for each label in ``trade_labels`` table."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT l.label,
                   COUNT(*) AS total,
                   SUM(CASE WHEN t.profit_loss > 0 THEN 1 ELSE 0 END) AS wins
            FROM trade_labels l
            JOIN trades t ON t.trade_id = l.trade_id
            GROUP BY l.label
            """
        )
        rows = cur.fetchall()
    return {r[0]: (r[2] / r[1]) if r[1] else 0.0 for r in rows}

__all__ = ["label_win_rates"]
