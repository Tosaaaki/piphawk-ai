from __future__ import annotations

"""OpenAI decision helper for the M5 pipeline."""

import logging

from backend.utils.openai_client import ask_openai

logger = logging.getLogger(__name__)


def call_llm(mode: str, signal: dict, indicators: dict) -> dict:
    """Ask OpenAI for final entry decision and TP/SL multipliers."""
    atr_series = indicators.get("atr")
    prompt = (
        f"mode: {mode}\n"
        f"signal: {signal.get('side')}\n"
        f"atr: {atr_series.iloc[-1] if atr_series is not None and not atr_series.empty else 'na'}\n"
        "Respond with JSON {\"go\":true/false, \"tp_mult\":float, \"sl_mult\":float}"
    )
    try:
        resp = ask_openai(
            prompt,
            system_prompt="You are a trading assistant. Respond in JSON only.",
        )
        if isinstance(resp, dict):
            return resp
    except Exception as exc:
        logger.warning("call_llm failed: %s", exc)
    return {"go": False}


__all__ = ["call_llm"]
