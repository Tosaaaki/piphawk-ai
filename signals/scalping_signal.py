from __future__ import annotations

"""M1 スキャルピング用シグナル生成."""

from analysis.ai_strategy.gpt_predictor import GPTPredictor
from filters.market_filters import is_tradeable

_predictor = GPTPredictor()


def make_signal(features: dict) -> str | None:
    """必ずエントリーする方向を返す."""
    if not is_tradeable(features.get("pair", ""), "M1", features.get("spread", 0.0)):
        return None
    probs = _predictor.predict(features)
    return "BUY" if probs["prob_long"] >= probs["prob_short"] else "SELL"

