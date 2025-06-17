from __future__ import annotations

"""Calculate atmosphere-related market features."""

from typing import Any, Sequence

from backend.indicators.vwap_band import get_vwap_bias


class AtmosphereFeatures:
    """Market feature extractor for atmosphere analysis."""

    def __init__(self, candles: Sequence[dict[str, Any]]) -> None:
        self.candles = list(candles)

    def vwap_bias(self) -> float:
        """Return VWAP bias of the latest close price."""
        prices = [float(c.get("close", c.get("c", 0))) for c in self.candles]
        volumes = [float(c.get("volume", c.get("v", 0))) for c in self.candles]
        return get_vwap_bias(prices, volumes)

    def volume_delta(self) -> float:
        """Return normalized volume delta (up minus down volume)."""
        up = 0.0
        down = 0.0
        for c in self.candles:
            vol = float(c.get("volume", c.get("v", 0)))
            open_p = float(c.get("open", c.get("o", 0)))
            close_p = float(c.get("close", c.get("c", 0)))
            if close_p >= open_p:
                up += vol
            else:
                down += vol
        total = up + down
        if total == 0:
            return 0.0
        return (up - down) / total

    def extract(self) -> dict[str, float]:
        """Return feature dictionary."""
        return {
            "vwap_bias": self.vwap_bias(),
            "volume_delta": self.volume_delta(),
        }


__all__ = ["AtmosphereFeatures"]
