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
from dataclasses import dataclass
from typing import Any, Dict

from backend.analysis.atmosphere import evaluate as atmos_eval
from backend.utils import env_loader, parse_json_answer
from backend.utils.openai_client import (
    ask_openai,
    num_tokens,
    trim_tokens,
)

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

# SCALE は含み益が伸びておりトレンドの継続が見込めると AI が判断したときに返る。
# リスク許容範囲を確認した上でポジションを追加する処理を想定している。

_ALLOWED_ACTIONS = {"EXIT", "HOLD", "SCALE"}


# ---------------------------------------------------------------------------
# environment helper (fallback if env_loader is unavailable)
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str | None = None) -> str | None:
    """Lightweight fallback to read env vars without env_loader."""
    return env_loader.get_env(key, default)


def to_serializable(obj: Any):
    """Recursively convert pandas Series or numpy arrays to lists."""
    try:
        import pandas as pd  # type: ignore
    except Exception:  # pragma: no cover - pandas may be absent
        pd = None
    try:
        import numpy as np  # type: ignore
    except Exception:  # pragma: no cover - numpy may be absent
        np = None

    if pd is not None and isinstance(obj, getattr(pd, "Series", ())):
        try:
            return [to_serializable(x) for x in obj.tolist()]
        except Exception:
            return []
    if np is not None and isinstance(obj, getattr(np, "ndarray", ())):
        try:
            return [to_serializable(x) for x in obj.tolist()]
        except Exception:
            return []
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(v) for v in obj]
    if hasattr(obj, "tolist") and not isinstance(obj, (str, bytes)):
        try:
            return [to_serializable(v) for v in obj.tolist()]
        except Exception:
            try:
                return obj.tolist()
            except Exception:
                pass
    return obj


def _build_prompt(context: Dict[str, Any], bias_factor: float = 1.0) -> str:
    """Compose the prompt including the bias factor and atmosphere info."""

    user_json = json.dumps(
        to_serializable(context), separators=(",", ":"), ensure_ascii=False
    )
    score, bias = atmos_eval(context)
    if bias > 0.2:
        bias_label = "Up"
    elif bias < -0.2:
        bias_label = "Down"
    else:
        bias_label = "Neutral"
    bias_line = f"BIAS_FACTOR={bias_factor} (>1 favors EXIT, <1 favors HOLD)."
    lines = [
        _SYSTEM_PROMPT,
        bias_line,
        f"### ATMOSPHERE SCORE\n{score:.2f}",
        f"### ATMOSPHERE BIAS\n{bias_label}",
        "USER_CONTEXT:",
        user_json,
    ]
    return "\n".join(lines)


def _parse_answer(raw: str | dict) -> AIDecision:
    """Parse the model answer which may be a dict or JSON string."""

    data, err = parse_json_answer(raw)
    if data is None:
        # Fallback – treat as HOLD with low confidence
        return AIDecision(action="HOLD", confidence=0.0, reason=f"json_error:{err}")

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

def evaluate(context: Dict[str, Any], bias_factor: float = 1.0) -> AIDecision:
    """Evaluate whether to exit using the provided *context* and bias factor.

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

    user_json = json.dumps(
        to_serializable(context), separators=(",", ":"), ensure_ascii=False
    )
    score, bias = atmos_eval(context)
    if bias > 0.2:
        bias_label = "Up"
    elif bias < -0.2:
        bias_label = "Down"
    else:
        bias_label = "Neutral"
    bias_line = f"BIAS_FACTOR={bias_factor} (>1 favors EXIT, <1 favors HOLD)."
    user_content = (
        f"{bias_line}\n"
        f"### ATMOSPHERE SCORE\n{score:.2f}\n"
        f"### ATMOSPHERE BIAS\n{bias_label}\n"
        f"USER_CONTEXT:\n{user_json}"
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    model = get_setting("AI_EXIT_MODEL", default="gpt-3.5-turbo-0125")
    temperature = float(get_setting("AI_EXIT_TEMPERATURE", default="0.0"))
    max_tokens = int(get_setting("AI_EXIT_MAX_TOKENS", default="128"))

    if num_tokens(messages, model=model) > 12000:
        messages = trim_tokens(messages, limit=12000, model=model)
    messages = trim_tokens(messages, limit=12000, model=model)

    raw = ask_openai(
        None,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )

    decision = _parse_answer(raw)
    decision.confidence = max(0.0, min(decision.confidence * bias_factor, 1.0))
    return decision
