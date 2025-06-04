"""H1 support level block filter."""

from backend.utils import env_loader


def _last_low(indicators: dict) -> float | None:
    """Extract the last low price from H1 indicators."""
    series = (
        indicators.get("low")
        or indicators.get("l")
        or indicators.get("lows")
    )
    try:
        if series is not None:
            if hasattr(series, "iloc"):
                return float(series.iloc[-1])
            if isinstance(series, (list, tuple)):
                return float(series[-1])
            return float(series)
        pivot = indicators.get("pivot")
        r1 = indicators.get("pivot_r1")
        if pivot is not None and r1 is not None:
            return 2 * float(pivot) - float(r1)
    except Exception:
        return None
    return None


def is_near_h1_support(indicators_h1: dict, price: float, rng: float) -> bool:
    """Return True if ``price`` is within ``rng`` pips of the last H1 low."""
    if not indicators_h1 or rng <= 0 or price is None:
        return False
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    low = _last_low(indicators_h1)
    if low is None or pip_size <= 0:
        return False
    diff_pips = abs(price - low) / pip_size
    return diff_pips <= rng

__all__ = ["is_near_h1_support"]
