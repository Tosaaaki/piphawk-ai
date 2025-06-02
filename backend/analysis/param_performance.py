from __future__ import annotations

"""Parameter change performance analysis."""

import sqlite3
import logging
from typing import Dict, Iterable, List, Tuple

try:
    # OpenAI 関連モジュールが無い場合でも本モジュールを利用できるようにする
    from backend.utils.openai_client import ask_openai
except Exception:
    ask_openai = None

from backend.logs.log_manager import DB_PATH as _DB_PATH

DB_PATH = str(_DB_PATH)


def _fetch_param_changes() -> List[Tuple[str, str, str]]:
    """Return list of (timestamp, param_name, new_value)."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT timestamp, param_name, new_value FROM param_changes ORDER BY timestamp"
        )
        return cur.fetchall()


def _group_changes(changes: Iterable[Tuple[str, str, str]]) -> List[dict]:
    """Group changes by timestamp."""
    grouped: List[dict] = []
    for ts, name, value in changes:
        if not grouped or grouped[-1]["timestamp"] != ts:
            grouped.append({"timestamp": ts, "params": {name: value}})
        else:
            grouped[-1]["params"][name] = value
    return grouped


def _fetch_trades(start: str, end: str | None) -> List[float]:
    """Fetch profit_loss values for trades between start and end."""
    query = (
        "SELECT profit_loss FROM trades "
        "WHERE exit_time IS NOT NULL AND entry_time >= ?"
    )
    params: List[str] = [start]
    if end:
        query += " AND entry_time < ?"
        params.append(end)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return [row[0] for row in cur.fetchall() if row[0] is not None]


def _calc_metrics(pnl: Iterable[float]) -> Dict[str, float | int]:
    vals = list(pnl)
    total = len(vals)
    wins = [p for p in vals if p > 0]
    losses = [p for p in vals if p <= 0]
    win_rate = len(wins) / total * 100 if total else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    net_pl = sum(vals)
    return {
        "trades": total,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "net_pl": net_pl,
    }


def analyze_param_performance() -> List[dict]:
    """Return performance metrics for each parameter change group."""
    raw = _fetch_param_changes()
    groups = _group_changes(raw)
    results = []
    for idx, g in enumerate(groups):
        start = g["timestamp"]
        end = groups[idx + 1]["timestamp"] if idx + 1 < len(groups) else None
        trades = _fetch_trades(start, end)
        metrics = _calc_metrics(trades)
        results.append({"timestamp": start, "params": g["params"], "metrics": metrics})
    return results


def suggest_best_params(perf: List[dict]) -> dict | None:
    """Ask OpenAI to recommend the best parameter set."""
    if not perf:
        return None

    lines = []
    for item in perf:
        ts = item["timestamp"]
        params = ", ".join(f"{k}={v}" for k, v in item["params"].items())
        m = item["metrics"]
        metrics = (
            f"trades={m['trades']} win_rate={m['win_rate']:.1f}% "
            f"net_pl={m['net_pl']:.2f} avg_win={m['avg_win']:.2f} avg_loss={m['avg_loss']:.2f}"
        )
        lines.append(f"[{ts}] {params} -> {metrics}")

    prompt = (
        "You are a trading strategy analyst.\n"
        "Below are parameter changes with their subsequent performance.\n"
        "Recommend the most effective parameter set.\n\n" +
        "\n".join(lines) +
        "\n\nRespond ONLY with JSON of parameter names and values."
    )
    if ask_openai is None:
        logging.getLogger(__name__).warning("OpenAI client unavailable; skipping suggestion")
        return None
    try:
        return ask_openai(prompt)
    except Exception as exc:
        logging.getLogger(__name__).error("OpenAI request failed: %s", exc)
    return None

__all__ = ["analyze_param_performance", "suggest_best_params"]
