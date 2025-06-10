import json
import logging

from backend.utils.openai_client import ask_openai
from backend.utils import env_loader, parse_json_answer

logger = logging.getLogger(__name__)

AI_SCALP_MODEL = env_loader.get_env("AI_SCALP_MODEL", "gpt-4.1-nano")
SCALP_PROMPT_BIAS = env_loader.get_env("SCALP_PROMPT_BIAS", "normal").lower()


def _series_tail_list(series, n: int = 20) -> list:
    """Return the last ``n`` values from a pandas Series or list."""
    if series is None:
        return []
    try:
        if hasattr(series, "iloc"):
            return series.iloc[-n:].tolist()
        if isinstance(series, (list, tuple)):
            return list(series)[-n:]
        return [series]
    except Exception:
        return []


def get_scalp_plan(indicators: dict, candles: list, *, higher_tf_direction: str | None = None) -> dict:
    """Return a trading plan specialized for scalping."""
    adx_vals = _series_tail_list(indicators.get("adx"), 5)
    rsi_vals = _series_tail_list(indicators.get("rsi"), 5)
    bb_upper = _series_tail_list(indicators.get("bb_upper"), 5)
    bb_lower = _series_tail_list(indicators.get("bb_lower"), 5)
    bias_note = ""
    if SCALP_PROMPT_BIAS == "aggressive":
        bias_note = (
            "\nAct decisively: choose 'long' or 'short' whenever possible. Return 'no' only if no valid setup exists."
        )
    prompt = (
        "You are a forex scalping assistant.\n"
        "Analyze the short-term indicators and decide whether to buy, sell or stay flat.\n"
        f"ADX:{adx_vals}\nRSI:{rsi_vals}\nBB_upper:{bb_upper}\nBB_lower:{bb_lower}\n"
        f"Candles:{candles[-20:]}\nHigher direction:{higher_tf_direction}\n"
        f"{bias_note}\n"
        "Respond with JSON as {\"side\":\"long|short|no\",\"tp_pips\":float,\"sl_pips\":float}"
    )
    try:
        raw = ask_openai(prompt, model=AI_SCALP_MODEL)
    except Exception as exc:  # pragma: no cover - network failure
        logger.warning("get_scalp_plan failed: %s", exc)
        return {"side": "no"}
    plan, _ = parse_json_answer(raw)
    if plan is None:
        return {"side": "no"}
    return plan


__all__ = ["get_scalp_plan", "AI_SCALP_MODEL", "SCALP_PROMPT_BIAS"]
