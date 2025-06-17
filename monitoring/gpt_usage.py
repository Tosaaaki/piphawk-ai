from __future__ import annotations

"""OpenAI 使用量を記録する簡易モジュール."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

_usage: Dict[str, float] = {"requests": 0.0, "tokens": 0.0, "usd": 0.0}


def add_usage(requests: int, tokens: int, usd: float) -> None:
    """利用量を加算する."""
    _usage["requests"] += requests
    _usage["tokens"] += tokens
    _usage["usd"] += usd
    logger.debug("GPT usage updated: %s", _usage)


def snapshot() -> Dict[str, float]:
    """現在の使用量を取得する."""
    return dict(_usage)

