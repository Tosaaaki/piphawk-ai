from __future__ import annotations

"""トレンド戦略向けのシグナル."""

from analysis.ai_strategy.gpt_predictor import GPTPredictor

_predictor = GPTPredictor()


def recheck(features: dict) -> dict:
    """プルバック中の再評価を行う."""
    features = dict(features)
    features["mode"] = "trend_pending"
    return _predictor.predict(features)

