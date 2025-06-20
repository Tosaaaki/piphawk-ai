"""Select trade strategy via OpenAI and majority vote."""
from __future__ import annotations

from collections import Counter
from typing import List, Tuple

from backend.utils import env_loader
from backend.utils.openai_client import ask_openai

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
            system_prompt=(
                "You are a trading strategy selector. Respond in JSON "
                "with keys trade_mode and prob between 0 and 1."
            ),
            model=AI_STRATEGY_MODEL,
            temperature=STRAT_TEMP,
            response_format={"type": "json_object"},
            n=n,
        )
    except Exception:
        resp_list = []

    if isinstance(resp_list, dict):
        results: List[Tuple[str, float]] = [
            (
                str(resp_list.get("trade_mode", "")).strip(),
                float(resp_list.get("prob", 0.0)),
            )
        ]
    else:
        results = [
            (
                str(r.get("trade_mode", "")).strip(),
                float(r.get("prob", 0.0)),
            )
            for r in resp_list
        ]

    results = [(m, p) for m, p in results if m]
    if not results:
        return "", False

    counts = Counter(m for m, _p in results)
    vote, cnt = counts.most_common(1)[0]
    if cnt >= STRAT_VOTE_MIN:
        return vote, True

    # 多数決が成立しない場合は確率が最大の案を採用
    top = max(results, key=lambda x: x[1])
    return top[0], False

__all__ = ["select_strategy"]
