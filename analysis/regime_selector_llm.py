from __future__ import annotations

"""LLM を用いた取引レジーム選択ユーティリティ."""

import json
import logging
from types import SimpleNamespace
from typing import Any, Dict, Tuple

from backend.utils import ai_parse
from backend.utils.openai_client import ask_openai

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a forex trading regime selector. "
    "Decide the mode from trend_follow, scalp_momentum, scalp_reversion, no_trade. "
    "Respond in JSON as {\"mode\":str, \"TREND\":0-1, \"BASE_SCALP\":0-1, \"REBOUND_SCALP\":0-1}."
)


def _to_snapshot(obj: Any) -> SimpleNamespace:
    if isinstance(obj, dict):
        return SimpleNamespace(**obj)
    return obj if hasattr(obj, "__dict__") else SimpleNamespace()


def select_mode(snapshot: Any) -> Tuple[str, Dict[str, float]]:
    """LLM に市場スナップショットを与えて取引モードを返す."""
    snap = _to_snapshot(snapshot)
    features = {
        "atr": getattr(snap, "atr", None),
        "news_score": getattr(snap, "news_score", None),
        "oi_bias": getattr(snap, "oi_bias", None),
    }
    prompt = json.dumps(features, ensure_ascii=False)
    try:
        raw = ask_openai(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            model="gpt-3.5-turbo-0125",
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data, err = ai_parse.parse_json_answer(raw)
        if err or not isinstance(data, dict):
            raise ValueError(err or "invalid response")
        mode = str(data.get("mode", "no_trade"))
        if mode not in {"trend_follow", "scalp_momentum", "scalp_reversion", "no_trade"}:
            mode = "no_trade"
        scores = {
            "TREND": float(data.get("TREND", 0.0)),
            "BASE_SCALP": float(data.get("BASE_SCALP", 0.0)),
            "REBOUND_SCALP": float(data.get("REBOUND_SCALP", 0.0)),
        }
        return mode, scores
    except Exception as exc:  # pragma: no cover - 外部要因
        logger.error("select_mode failed: %s", exc)
        return "no_trade", {"TREND": 0.0, "BASE_SCALP": 0.0, "REBOUND_SCALP": 0.0}


__all__ = ["select_mode"]
