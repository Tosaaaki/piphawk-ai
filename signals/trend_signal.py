from __future__ import annotations

"""トレンド戦略向けのシグナル."""

from analysis.ai_strategy.gpt_predictor import GPTPredictor
from filters.market_filters import is_tradeable

_predictor = GPTPredictor()


def recheck(features: dict) -> dict | None:
    """プルバック中の再評価を行う."""
    if not is_tradeable(
        features.get("pair", ""),
        features.get("timeframe", "M5"),
        features.get("spread", 0.0),
        features.get("atr"),
    ):
        return None
    features = dict(features)
    features["mode"] = "trend_pending"
    return _predictor.predict(features)

