from __future__ import annotations

"""Convert atmosphere features to a score."""

from typing import Mapping


class AtmosphereScore:
    """特徴量を 0-100 点に正規化するクラス."""

    def __init__(self, weights: Mapping[str, float] | None = None) -> None:
        self.weights = {
            "vwap_bias": 0.5,
            "volume_delta": 0.5,
        }
        if weights:
            self.weights.update(weights)

    def calc(self, features: Mapping[str, float]) -> float:
        """Return total score from features."""
        bias = abs(float(features.get("vwap_bias", 0.0)))
        delta = float(features.get("volume_delta", 0.0))
        bias_score = min(bias * 2000, 100.0)
        delta_score = (delta + 1) * 50
        total = (
            bias_score * self.weights.get("vwap_bias", 0)
            + delta_score * self.weights.get("volume_delta", 0)
        )
        return max(0.0, min(total, 100.0))


__all__ = ["AtmosphereScore"]
