from __future__ import annotations

"""Helper for LLM mode scoring."""

import json
import logging
from typing import Any, Dict

from backend.utils.openai_client import ask_openai

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a forex trading mode scorer."
    " Evaluate how appropriate each trading mode is given the market snapshot."
    " Respond strictly with JSON as {\"TREND\":0-1,\"BASE_SCALP\":0-1,\"REBOUND_SCALP\":0-1}."
)


def get_mode_scores(snapshot: Any) -> Dict[str, float]:
    """Return LLM mode scores for the given snapshot."""
    prompt = json.dumps(
        {
            "atr": getattr(snapshot, "atr", None),
            "news_score": getattr(snapshot, "news_score", None),
            "oi_bias": getattr(snapshot, "oi_bias", None),
        },
        ensure_ascii=False,
    )
    try:
        raw = ask_openai(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            model="gpt-3.5-turbo-0125",
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = raw if isinstance(raw, dict) else json.loads(str(raw))
    except Exception as exc:  # pragma: no cover - network failures
        logger.error("get_mode_scores failed: %s", exc)
        return {"TREND": 0.0, "BASE_SCALP": 0.0, "REBOUND_SCALP": 0.0}
    result = {}
    for key in ("TREND", "BASE_SCALP", "REBOUND_SCALP"):
        try:
            result[key] = float(data.get(key, 0.0))
        except Exception:
            result[key] = 0.0
    return result


__all__ = ["get_mode_scores"]
