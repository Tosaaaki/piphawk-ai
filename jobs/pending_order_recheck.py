from __future__ import annotations

"""未約定指値を再評価するジョブ."""

from signals.trend_signal import recheck


def handle(ticket: str, features: dict) -> dict:
    """シグナルに基づき注文の扱いを決める."""
    probs = recheck(features)
    if probs["prob_long"] > 0.6:
        return {"action": "keep"}
    if probs["prob_long"] <= 0.6 and probs["prob_short"] <= 0.6:
        return {"action": "market"}
    if probs["prob_short"] > 0.6:
        return {"action": "cancel"}
    return {"action": "keep"}

