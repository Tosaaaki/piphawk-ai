from __future__ import annotations

"""Market snapshot utilities for the technical pipeline."""

from dataclasses import dataclass
from backend.market_data.candle_fetcher import fetch_candles
from backend.market_data.tick_fetcher import fetch_tick_data
from backend.utils import env_loader


@dataclass
class MarketContext:
    """Container for recent market data."""

    candles: list[dict]
    tick: dict | None
    spread: float
    account: dict | None = None


def build() -> MarketContext:
    """Fetch latest market data and return a context object."""
    pair = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    candles = fetch_candles(pair, granularity="M5", count=60)
    tick = fetch_tick_data(pair)
    spread = 0.0
    try:
        price = tick.get("prices", [])[0]
        bid = float(price.get("bids", [])[0]["price"])
        ask = float(price.get("asks", [])[0]["price"])
        spread = ask - bid
    except Exception:
        spread = 0.0
    return MarketContext(candles=candles, tick=tick, spread=spread)


__all__ = ["MarketContext", "build"]
