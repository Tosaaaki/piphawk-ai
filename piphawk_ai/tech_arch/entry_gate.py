from __future__ import annotations

"""LLM entry gate for the technical pipeline."""

from backend.utils.openai_client import ask_openai


def ask_entry(mode: str, indicators: dict) -> dict | None:
    """Return trade plan dict or ``None`` when rejected."""
    prompt = (
        f"mode: {mode}\n"
        f"ema_fast: {indicators.get('ema_fast')[-1] if indicators.get('ema_fast') is not None else 'na'}\n"
        f"ema_slow: {indicators.get('ema_slow')[-1] if indicators.get('ema_slow') is not None else 'na'}\n"
        "Respond with JSON {\"enter\":true/false, \"side\":\"long|short\", \"tp\":pips, \"sl\":pips}"
    )
    try:
        resp = ask_openai(prompt, system_prompt="You are a trading entry gate. Respond in JSON only.")
    except Exception:
        return None
    if not isinstance(resp, dict) or not resp.get("enter"):
        return None
    return resp


__all__ = ["ask_entry"]
