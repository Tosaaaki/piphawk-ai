from __future__ import annotations

"""LLM を用いたモード選択ラッパー."""

import json
import logging
from pathlib import Path

import yaml

from backend.utils import ai_parse
from backend.utils.openai_client import ask_openai

logger = logging.getLogger(__name__)

_cfg: dict | None = None


def _load_cfg() -> dict:
    global _cfg
    if _cfg is None:
        path = Path(__file__).resolve().parents[1] / "config" / "strategy.yml"
        try:
            with path.open("r", encoding="utf-8") as f:
                _cfg = yaml.safe_load(f) or {}
        except Exception:
            _cfg = {}
    return _cfg


_cfg = _load_cfg()
_MODEL = _cfg.get("LLM", {}).get("mode_selector", "gpt-4.1-nano")
_SYSTEM_PROMPT = (
    "You are a FX trading mode selector. "
    "Return one of ['trend_follow','scalp_momentum','no_trade'] "
    'in JSON: {"mode":"..."}'
)


def select_mode_llm(features: dict) -> str:
    """LLM を利用してモードを選択する."""
    try:
        raw = ask_openai(
            json.dumps(features),
            system_prompt=_SYSTEM_PROMPT,
            model=_MODEL,
            temperature=0.0,
        )
        data, err = ai_parse.parse_json_answer(raw)
        if err:
            return "no_trade"
        mode = str(data.get("mode"))
        if mode in {"trend_follow", "scalp_momentum", "no_trade"}:
            return mode
    except Exception as exc:
        logger.error("select_mode_llm failed: %s", exc)
    return "no_trade"


__all__ = ["select_mode_llm"]
