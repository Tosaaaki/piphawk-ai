"""AI‑based exit decision module.

Provides a thin wrapper around OpenAI to decide whether an open position
should be exited, held, or scaled.  Designed to be called *occasionally*
(event‑driven) by `job_runner.py` when certain risk triggers fire.

Usage (pseudo):
    ctx = build_context(position, market)
    decision = exit_ai_decision.evaluate(ctx)
    if decision.action == "EXIT" and decision.confidence > 0.6:
        order_manager.exit_trade(position)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from backend.utils.openai_client import ask_openai  # existing helper that wraps OpenAI ChatCompletion

__all__ = ["AIDecision", "evaluate"]


@dataclass(slots=True)
class AIDecision:
    """Return type of *evaluate*.

    Attributes
    ----------
    action : str
        One of ``EXIT``, ``HOLD``, ``SCALE``.
    confidence : float
        0‑1 range.  The calling code decides the threshold.
    reason : str
        Short textual explanation for logging / later analysis.
    """

    action: str = "HOLD"
    confidence: float = 0.0
    reason: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "confidence": self.confidence,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an expert foreign‑exchange risk manager and trading coach. "
    "Given the current trading context you must respond with a strict JSON "
    "object using exactly the keys: action, confidence, reason.\n\n"
    "Allowed values for *action* are EXIT, HOLD, SCALE.\n"
    "*confidence* must be a number between 0 and 1.\n"
    "*reason* must be a single short English sentence (max 25 words).\n"
    "Do not wrap the JSON in markdown."
)

_ALLOWED_ACTIONS = {"EXIT", "HOLD", "SCALE"}


# ---------------------------------------------------------------------------
# environment helper (fallback if env_loader is unavailable)
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str | None = None) -> str | None:
    """Lightweight fallback to read env vars without env_loader."""
    return os.getenv(key, default)


def _build_prompt(context: Dict[str, Any]) -> str:
    """Compose the prompt (system + user JSON)."""

    user_json = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    return f"{_SYSTEM_PROMPT}\nUSER_CONTEXT:\n{user_json}"


def _parse_answer(raw: str) -> AIDecision:
    """Parse the model answer (expected raw JSON)."""

    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        # Fallback – treat as HOLD with low confidence
        return AIDecision(action="HOLD", confidence=0.0, reason=f"json_error:{exc}")

    action = str(data.get("action", "HOLD")).upper()
    if action not in _ALLOWED_ACTIONS:
        action = "HOLD"

    try:
        conf = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0

    reason = str(data.get("reason", ""))[:120]

    return AIDecision(action=action, confidence=conf, reason=reason)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def evaluate(context: Dict[str, Any]) -> AIDecision:
    """Evaluate whether to exit using the provided *context*.

    Parameters
    ----------
    context : dict
        Must be JSON‑serialisable.  Recommended keys: side, units, avg_price,
        unrealized_pl_pips, entry_ts, bid, ask, spread_pips, atr_pips,
        rsi, ema_slope, recent_losses, h1_trend, etc.

    Returns
    -------
    AIDecision
        Parsed decision from the language model.
    """

    prompt = _build_prompt(context)

    model = get_setting("AI_EXIT_MODEL", default="gpt-4o-mini")
    temperature = float(get_setting("AI_EXIT_TEMPERATURE", default="0.0"))
    max_tokens = int(get_setting("AI_EXIT_MAX_TOKENS", default="128"))

    raw = ask_openai(
        prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return _parse_answer(raw)