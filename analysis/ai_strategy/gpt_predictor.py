from __future__ import annotations

"""GPT-3.5 を利用した確率予測ラッパー."""

import json
import os

import openai
from tenacity import retry, stop_after_attempt, wait_random_exponential

from monitoring.gpt_usage import add_usage

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_SYSTEM_PROMPT = """\
You are a quantitative FX trading brain.
Input: a JSON object with numeric features (= 1 candle or tick snapshot).
Goal: output *only* a JSON object with keys
  prob_long, prob_short, prob_flat  (float, 0.0-1.0, sum≈1.0).
No explanations, no extra keys.
Rules:
- If 'mode' == 'scalping', you must always choose either long or short
  (prob_flat ≤ 0.05).
- If 'mode' starts with 'trend', flat is allowed.
- Be deterministic: temperature=0 is enforced on the client.
"""


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(5))
def _ask_gpt(messages: list[dict]) -> dict:
    """内部用: GPT へ問い合わせる."""
    resp = openai_client.chat.completions.create(
        model="gpt-4.1-nano",
        temperature=0,
        response_format={"type": "json_object"},
        messages=messages,
        timeout=8,
    )
    usage = resp.usage
    add_usage(1, usage.total_tokens, usage.total_tokens * 0.000002)
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError as exc:
        raise exc


def _validate_probs(d: dict) -> dict:
    """必須キーを確認する."""
    for k in ("prob_long", "prob_short", "prob_flat"):
        if k not in d:
            raise KeyError(f"Missing key {k} in GPT response")
    return d


class GPTPredictor:
    """features 辞書から確率を取得するシンプルなクラス."""

    def __init__(self) -> None:  # noqa: D401 - 単純な初期化
        pass

    def predict(self, features: dict) -> dict:
        """特徴量辞書を与えて確率辞書を返す."""
        user_msg = json.dumps(features, separators=(",", ":"))
        msgs = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        return _validate_probs(_ask_gpt(msgs))
