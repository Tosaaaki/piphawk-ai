from __future__ import annotations

"""Utility functions to build context vectors for strategy selection."""


import sqlite3

from backend.logs.log_manager import get_db_connection, init_db


def recent_strategy_performance(limit: int = 10) -> Dict[str, float]:
    """Return average reward for each strategy over recent transitions."""
    perf: Dict[str, list[float]] = {}
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT action, reward FROM policy_transitions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            init_db()
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT action, reward FROM policy_transitions ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cur.fetchall()
        else:
            raise
    for action, reward in rows:
        perf.setdefault(action, []).append(float(reward))
    return {k: sum(v) / len(v) for k, v in perf.items() if v}


def build_context(regime: str, indicators: Dict[str, Any], perf: Dict[str, float] | None = None) -> Dict[str, float]:
    """Assemble context dictionary for StrategySelector."""
    ctx: Dict[str, float] = {
        "regime_trend": 1.0 if regime == "TREND" else 0.0,
    }
    try:
        adx_series = indicators.get("adx")
        if adx_series is not None:
            val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
            ctx["adx"] = float(val)
    except Exception:
        pass
    try:
        atr_series = indicators.get("atr")
        if atr_series is not None:
            val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            ctx["atr"] = float(val)
    except Exception:
        pass
    if perf:
        for k, v in perf.items():
            ctx[f"{k}_perf"] = float(v)
    return ctx


__all__ = ["build_context", "recent_strategy_performance"]
