from __future__ import annotations

"""GPT-3.5 を利用した確率予測ラッパー."""

import json
import os

import openai
from tenacity import retry, stop_after_attempt, wait_random_exponential

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
        model="gpt-3.5-turbo-1106",
        temperature=0,
        response_format={"type": "json_object"},
        messages=messages,
        timeout=8,
    )
    return json.loads(resp.choices[0].message.content)


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
        return _ask_gpt(msgs)
