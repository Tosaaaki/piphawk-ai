from __future__ import annotations

"""AI-driven exit adjustment helper."""

import json
from typing import Any, Dict

from backend.utils.openai_client import ask_openai
from backend.utils import env_loader, parse_json_answer

try:
    from backend.logs.log_manager import (
        log_ai_decision,
        log_prompt_response,
        log_exit_adjust,
    )
except Exception:  # pragma: no cover - during tests

    def log_ai_decision(*_a, **_k) -> None:
        pass

    def log_prompt_response(*_a, **_k) -> None:
        pass

    def log_exit_adjust(*_a, **_k) -> None:
        pass


_SYSTEM_PROMPT = (
    "You are a professional FX risk manager. "
    "Suggest how to adjust take-profit or stop-loss. "
    "Respond with JSON {\"action\":,\"tp\":,\"sl\":}. "
    "Actions: HOLD, REDUCE_TP, MOVE_BE, SHRINK_SL."
)


def propose_exit_adjustment(context: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the LLM for TP/SL adjustment proposals."""
    prompt = "CONTEXT:\n" + json.dumps(context, ensure_ascii=False)
    model = env_loader.get_env("AI_EXIT_MODEL", "gpt-4.1-nano")
    temperature = float(env_loader.get_env("AI_EXIT_TEMPERATURE", "0.0"))
    max_tokens = int(env_loader.get_env("AI_EXIT_MAX_TOKENS", "64"))
    try:
        raw = ask_openai(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # pragma: no cover - network issues
        log_ai_decision("EXIT_ADJUST_ERROR", context.get("instrument", ""), str(exc))
        return {"action": "HOLD", "tp": None, "sl": None}

    try:
        log_prompt_response(
            "EXIT_ADJUST",
            context.get("instrument", ""),
            prompt,
            json.dumps(raw, ensure_ascii=False),
        )
    except Exception:
        pass

    data, _ = parse_json_answer(raw)
    if data is None:
        return {"action": "HOLD", "tp": None, "sl": None}

    action = str(data.get("action", "HOLD")).upper()
    return {"action": action, "tp": data.get("tp"), "sl": data.get("sl")}


__all__ = ["propose_exit_adjustment"]
