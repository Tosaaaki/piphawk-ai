from __future__ import annotations

"""Scalp momentum utilities."""

from typing import Any

from backend.utils import env_loader
from backend.indicators.ema import get_ema_gradient


def exit_if_momentum_loss(indicators: dict[str, Any]) -> bool:
    """Return True when EMA gradient turns down and RSI/MACD confirm weakness."""
    ema_fast = indicators.get("ema_fast")
    rsi_series = indicators.get("rsi")
    macd_hist = indicators.get("macd_hist")
    if ema_fast is None or rsi_series is None or macd_hist is None:
        return False

    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    try:
        ema_dir = get_ema_gradient(ema_fast, pip_size=pip_size)
    except Exception:
        ema_dir = "flat"

    try:
        rsi_val = float(rsi_series.iloc[-1]) if hasattr(rsi_series, "iloc") else float(rsi_series[-1])
        macd_val = float(macd_hist.iloc[-1]) if hasattr(macd_hist, "iloc") else float(macd_hist[-1])
    except Exception:
        return False

    if ema_dir == "down" and rsi_val < 50 and macd_val < 0:
        return True
    return False


__all__ = ["exit_if_momentum_loss"]
