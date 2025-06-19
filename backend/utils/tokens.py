"""Token counting helpers."""
from __future__ import annotations

import json
from typing import Dict, List

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None


def num_tokens(messages: List[Dict[str, str]], model: str = "gpt-4.1-nano") -> int:
    """Return token count for chat messages."""

    if tiktoken is None:
        return sum(len(m.get("content", "")) // 4 for m in messages)

    enc = tiktoken.encoding_for_model(model)
    tokens_per_msg = 4
    tokens_per_name = -1
    if model.startswith("gpt-4"):
        tokens_per_msg = 3
        tokens_per_name = 1
    n = 0
    for msg in messages:
        n += tokens_per_msg
        for k, v in msg.items():
            n += len(enc.encode(v))
            if k == "name":
                n += tokens_per_name
    return n + 3


def ensure_under_limit(messages: List[Dict[str, str]], limit: int = 1800) -> None:
    """Shrink bars in messages until token count is under limit."""
    if len(messages) < 2:
        return
    try:
        ctx = json.loads(messages[1]["content"])
    except Exception:
        return
    while num_tokens(messages) > limit and ctx.get("bars"):
        ctx["bars"] = ctx["bars"][::2]
        messages[1]["content"] = json.dumps(ctx, separators=(",", ":"))

