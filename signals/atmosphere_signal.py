from __future__ import annotations

"""Simple entry signal using atmosphere score and RSI."""

from typing import Mapping

from analysis.atmosphere.regime_classifier import RegimeClassifier


def generate_signal(score: float, rsi: float, *, classifier: RegimeClassifier | None = None) -> str | None:
    """Return order side if conditions meet."""
    classifier = classifier or RegimeClassifier()
    tag = classifier.classify(score)
    if tag == "Risk-On" and rsi < 30:
        return "long"
    if tag == "Risk-Off" and rsi > 70:
        return "short"
    return None


__all__ = ["generate_signal"]
