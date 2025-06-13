"""LLMを用いたエントリー決定とTP倍率チューニング."""
from __future__ import annotations

import json
from backend.utils.openai_client import ask_openai


def call_llm(payload: dict) -> dict | None:
    """OpenAI に問い合わせて結果を返す."""
    prompt = json.dumps(payload, ensure_ascii=False)
    try:
        resp = ask_openai(
            prompt,
            system_prompt=(
                "You are a trading assistant. Return JSON {\"decision\":\"GO|PASS\","
                " \"tp_mult\":number, \"sl_mult\":number}"
            ),
        )
    except Exception:
        return None
    if not isinstance(resp, dict):
        return None
    return resp


__all__ = ["call_llm"]
