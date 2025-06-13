from __future__ import annotations

"""Simple trade mode detector without LLM."""

from .mode_preclassifier import classify_regime

# Map regime categories to trade modes
_REGIME_TO_MODE = {
    "trend": "trend_follow",
    "range": "scalp_momentum",
}


def detect_mode_simple(features: dict) -> str:
    """Return trade mode based on preclassifier only."""
    regime = classify_regime(features)
    return _REGIME_TO_MODE.get(regime, "no_trade")

__all__ = ["detect_mode_simple"]

"""Rule-based trade mode detection."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from backend.utils import env_loader


@dataclass
class MarketContext:
    """Container for recent price and indicators."""

    price: float
    indicators: Dict[str, Any]


def _last_val(series):
    if series is None:
        return None
    try:
        if hasattr(series, "iloc"):
            return float(series.iloc[-1]) if len(series) else None
        if isinstance(series, (list, tuple)):
            return float(series[-1]) if series else None
        return float(series)
    except Exception:
        return None


def detect_mode(ctx: MarketContext) -> str:
    """Return trade mode from simple rule set."""

    cfg = _PARAMS or load_config()

    ind = ctx.indicators
    atr = _last_val(ind.get("atr"))
    adx = _last_val(ind.get("adx"))

    adx_min = float(env_loader.get_env("ADX_TREND_MIN", str(cfg["adx_trend_min"])))
    low_adx_thr = float(env_loader.get_env("ADX_RANGE_MAX", str(cfg["adx_range_max"])))
    atr_min = float(env_loader.get_env("ATR_PCT_MIN", str(cfg["atr_pct_min"])))

    ema_fast = _last_val(ind.get("ema_fast") or ind.get("ema14"))
    ema_mid = _last_val(ind.get("ema_mid") or ind.get("ema50"))
    ema_slow = _last_val(ind.get("ema_slow") or ind.get("ema200"))

    perfect_order = False
    if None not in (ema_fast, ema_mid, ema_slow):
        if (ema_fast > ema_mid > ema_slow) or (ema_fast < ema_mid < ema_slow):
            perfect_order = True

    if atr is not None and adx is not None:
        if atr >= atr_min and adx <= low_adx_thr:
            return "scalp_momentum"

    if adx is not None and adx >= adx_min and perfect_order:
        return "trend_follow"

    if adx is not None and adx >= adx_min / 2:
        return "scalp_momentum"

    return "flat"

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "mode_detector.yml"

_DEFAULT_PARAMS = {
    "adx_trend_min": 25,
    "adx_range_max": 18,
    "atr_pct_min": 0.003,
    "ema_slope_min": 0.1,
}

_PARAMS: dict | None = None


def _load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception:
        return {}


def load_config(path: str | Path | None = None) -> dict:
    """Return detector thresholds from YAML with defaults applied."""
    global _PARAMS
    if path is None:
        path = env_loader.get_env("MODE_DETECTOR_CONFIG", str(_DEFAULT_PATH))
    p = Path(path)
    cfg = _load_yaml(p)
    merged = {**_DEFAULT_PARAMS, **cfg}
    _PARAMS = merged
    return merged


__all__ = ["MarketContext", "detect_mode", "detect_mode_simple", "load_config"]
