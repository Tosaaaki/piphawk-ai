from __future__ import annotations
"""Composite trade mode decision utility."""

from typing import Sequence, Iterable
import logging

from backend.utils import env_loader

MODE_ATR_PIPS_MIN = float(env_loader.get_env("MODE_ATR_PIPS_MIN", "5"))
MODE_BBWIDTH_PIPS_MIN = float(env_loader.get_env("MODE_BBWIDTH_PIPS_MIN", "3"))
MODE_EMA_SLOPE_MIN = float(env_loader.get_env("MODE_EMA_SLOPE_MIN", "0.1"))
MODE_ADX_MIN = float(env_loader.get_env("MODE_ADX_MIN", "25"))
MODE_VOL_MA_MIN = float(env_loader.get_env("MODE_VOL_MA_MIN", env_loader.get_env("MIN_VOL_MA", "80")))
VOL_MA_PERIOD = int(env_loader.get_env("VOL_MA_PERIOD", "5"))


def _last(value: Iterable | Sequence | None) -> float | None:
    """Return last element from list or pandas Series."""
    if value is None:
        return None
    try:
        if hasattr(value, "iloc"):
            if len(value):
                return float(value.iloc[-1])
            return None
        if isinstance(value, Sequence) and value:
            return float(value[-1])
    except Exception:
        return None
    return None


def decide_trade_mode(indicators: dict) -> str:
    """Return ``trend_follow`` or ``scalp`` based on three factors."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    atr = _last(indicators.get("atr")) or 0.0
    bb_u = _last(indicators.get("bb_upper"))
    bb_l = _last(indicators.get("bb_lower"))
    bb_width_pips = 0.0
    if bb_u is not None and bb_l is not None:
        bb_width_pips = (float(bb_u) - float(bb_l)) / pip_size
    atr_pips = float(atr) / pip_size
    volatility = atr_pips >= MODE_ATR_PIPS_MIN or bb_width_pips >= MODE_BBWIDTH_PIPS_MIN

    ema_slope = _last(indicators.get("ema_slope"))
    macd_hist = _last(indicators.get("macd_hist"))
    adx = _last(indicators.get("adx"))
    mom_checks = [
        abs(ema_slope) >= MODE_EMA_SLOPE_MIN if ema_slope is not None else False,
        abs(macd_hist) >= MODE_EMA_SLOPE_MIN if macd_hist is not None else False,
        adx is not None and adx >= MODE_ADX_MIN,
    ]
    momentum = sum(mom_checks) >= 2

    vol_series = indicators.get("volume")
    liquidity = True
    if vol_series is not None and len(vol_series) >= VOL_MA_PERIOD:
        if hasattr(vol_series, "iloc"):
            recent = vol_series.iloc[-VOL_MA_PERIOD:]
        else:
            recent = vol_series[-VOL_MA_PERIOD:]
        try:
            avg_vol = sum(float(v) for v in recent) / len(recent)
            liquidity = avg_vol >= MODE_VOL_MA_MIN
        except Exception:
            liquidity = True

    score = sum([volatility, momentum, liquidity])
    mode = "trend_follow" if score >= 2 else "scalp"
    logging.getLogger(__name__).info("decide_trade_mode -> %s (score=%d)", mode, score)
    return mode


__all__ = [
    "decide_trade_mode",
    "MODE_ATR_PIPS_MIN",
    "MODE_BBWIDTH_PIPS_MIN",
    "MODE_EMA_SLOPE_MIN",
    "MODE_ADX_MIN",
    "MODE_VOL_MA_MIN",
]
