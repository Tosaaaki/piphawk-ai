import json
import logging
from pathlib import Path

from backend.utils import env_loader, parse_json_answer
from backend.utils.openai_client import ask_openai

logger = logging.getLogger(__name__)

MICRO_SCALP_MODEL = env_loader.get_env("MICRO_SCALP_MODEL", "gpt-4.1-nano")

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "scalp_llm_prompt.txt"


def load_prompt() -> str:
    """Return prompt text for micro-scalp analysis."""
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:  # pragma: no cover - file issues
        logger.error("Failed to load micro scalp prompt: %s", exc)
        return ""


def get_plan(features: dict) -> dict:
    """Return micro-scalp trade plan based on predefined prompt."""
    prompt = load_prompt()
    try:
        raw = ask_openai(prompt, model=MICRO_SCALP_MODEL)
    except Exception as exc:  # pragma: no cover - network failure
        logger.warning("get_plan failed: %s", exc)
        return {"enter": False}
    plan, _ = parse_json_answer(raw)
    if plan is None:
        return {"enter": False}
    return plan


__all__ = ["get_plan", "MICRO_SCALP_MODEL", "load_prompt", "PROMPT_PATH"]
