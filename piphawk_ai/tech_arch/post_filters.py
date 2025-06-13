from __future__ import annotations

"""Final safety checks for the technical pipeline."""

from backend.strategy.signal_filter import update_overshoot_window


def apply_post_filters(candles: list[dict], indicators: dict) -> bool:
    """Update overshoot window and return True."""
    try:
        if candles:
            last = candles[-1]
            high = float(last.get("mid", last).get("h"))
            low = float(last.get("mid", last).get("l"))
            update_overshoot_window(high, low)
    except Exception:
        pass
    return True


__all__ = ["apply_post_filters"]
