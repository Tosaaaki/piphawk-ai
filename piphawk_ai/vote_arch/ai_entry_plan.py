"""Deterministic entry plan generation via OpenAI."""
from __future__ import annotations

from dataclasses import dataclass

from backend.utils import env_loader
from backend.utils.openai_client import ask_openai

AI_ENTRY_MODEL = env_loader.get_env("AI_ENTRY_MODEL", "gpt-4.1-nano")

@dataclass
class EntryPlan:
    side: str
    tp: float
    sl: float
    lot: float


def generate_plan(prompt: str) -> EntryPlan | None:
    """Return EntryPlan from AI."""
    resp = ask_openai(
        prompt,
        system_prompt=(
            "You are a trading entry planner. Respond in JSON format."
        ),
        model=AI_ENTRY_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    try:
        return EntryPlan(
            side=str(resp["side"]),
            tp=float(resp["tp"]),
            sl=float(resp["sl"]),
            lot=float(resp.get("lot", 1.0)),
        )
    except Exception:
        return None

__all__ = ["EntryPlan", "generate_plan"]
