"""Wrapper for market air utilities (deprecated)."""
from analysis.atmosphere.market_air_sensor import MarketSnapshot, air_index

# 互換性維持のための薄いラッパー

__all__ = ["MarketSnapshot", "air_index"]
