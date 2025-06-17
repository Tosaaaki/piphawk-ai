from __future__ import annotations

"""Atmosphere evaluation utilities."""

from typing import Any, Sequence

from analysis.atmosphere.feature_extractor import AtmosphereFeatures
from analysis.atmosphere.score_calculator import AtmosphereScore


def evaluate(context: dict[str, Any]) -> tuple[float, float]:
    """Return atmosphere score (0-1) and bias."""
    candles: Sequence[dict[str, Any]] = (
        context.get("candles")
        or context.get("candles_m5")
        or context.get("candles_M5")
        or []
    )
    try:
        features = AtmosphereFeatures(candles).extract() if candles else {}
    except Exception:
        features = {}
    score_raw = AtmosphereScore().calc(features) if features else 0.0
    score = score_raw / 100.0
    bias = float(features.get("vwap_bias", 0.0))
    return score, bias


__all__ = ["evaluate"]
