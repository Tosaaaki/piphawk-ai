from __future__ import annotations

"""Classify market regime based on atmosphere score."""


class RegimeClassifier:
    """スコアをタグへ変換する単純な分類クラス."""

    def __init__(self, on_threshold: float = 70.0, off_threshold: float = 30.0) -> None:
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold

    def classify(self, score: float) -> str:
        """Return regime tag from score."""
        if score >= self.on_threshold:
            return "Risk-On"
        if score <= self.off_threshold:
            return "Risk-Off"
        return "Neutral"


__all__ = ["RegimeClassifier"]
