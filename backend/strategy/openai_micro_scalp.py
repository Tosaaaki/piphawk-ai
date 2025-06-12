import json
import logging

from backend.utils.openai_client import ask_openai
from backend.utils import env_loader, parse_json_answer

logger = logging.getLogger(__name__)

MICRO_SCALP_MODEL = env_loader.get_env("MICRO_SCALP_MODEL", "gpt-4.1-nano")


def get_plan(features: dict) -> dict:
    """Return micro-scalp trade plan based on tick features."""
    prompt = (
        "You are a forex micro-scalping assistant.\n"
        "Decide whether to open a very short-term trade.\n"
        f"OF_imbalance:{features.get('of_imbalance')}\n"
        f"Vol_burst:{features.get('vol_burst')}\n"
        f"Avg_spread_pips:{features.get('spd_avg')}\n"
        "Respond with JSON as {\"enter\":true|false,\"side\":\"long|short\",\"tp_pips\":float,\"sl_pips\":float}"
    )
    try:
        raw = ask_openai(prompt, model=MICRO_SCALP_MODEL)
    except Exception as exc:  # pragma: no cover - network failure
        logger.warning("get_plan failed: %s", exc)
        return {"enter": False}
    plan, _ = parse_json_answer(raw)
    if plan is None:
        return {"enter": False}
    return plan


__all__ = ["get_plan", "MICRO_SCALP_MODEL"]
