"""Select trade strategy via OpenAI and majority vote."""
from __future__ import annotations

from collections import Counter

from backend.utils.openai_client import ask_openai
from backend.utils import env_loader

AI_STRATEGY_MODEL = env_loader.get_env("AI_STRATEGY_MODEL", "gpt-4.1-nano")
STRAT_TEMP = float(env_loader.get_env("STRAT_TEMP", "0.15"))
STRAT_N = int(env_loader.get_env("STRAT_N", "3"))
STRAT_VOTE_MIN = int(env_loader.get_env("STRAT_VOTE_MIN", "2"))


def select_strategy(prompt: str, n: int | None = None) -> tuple[str, bool]:
    """Return voted trade mode and bool indicating majority."""
    if n is None:
        n = STRAT_N
    try:
        resp_list = ask_openai(
            prompt,
            system_prompt="You are a trading strategy selector.",
            model=AI_STRATEGY_MODEL,
            temperature=STRAT_TEMP,
            response_format={"type": "json_object"},
            n=n,
        )
    except Exception:
        resp_list = []
    if isinstance(resp_list, dict):
        modes = [str(resp_list.get("trade_mode", "")).strip()]
    else:
        modes = [str(r.get("trade_mode", "")).strip() for r in resp_list]
    modes = [m for m in modes if m]
    if not modes:
        return "", False
    vote, cnt = Counter(modes).most_common(1)[0]
    return vote, cnt >= STRAT_VOTE_MIN

__all__ = ["select_strategy"]
