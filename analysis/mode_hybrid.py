from __future__ import annotations

"""Hybrid trade mode detection utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml

from analysis.llm_client import get_mode_scores
from analysis.mode_preclassifier import classify_regime
from backend.utils import env_loader


@dataclass
class MarketContext:
    """Container for recent price and indicator values."""

    price: float
    indicators: Dict[str, Any]


_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "mode_detector.yml"
_DEFAULT_PARAMS = {
    "adx_trend_min": 25,
    "adx_range_max": 18,
    "atr_pct_min": 0.003,
    "ema_slope_min": 0.1,
    "TREND_STR_THLD": 0.7,
    "RANGE_SCORE_THLD": 0.7,
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
    """Load detector thresholds with defaults applied."""
    global _PARAMS
    if path is None:
        path = env_loader.get_env("MODE_DETECTOR_CONFIG", str(_DEFAULT_PATH))
    cfg = _load_yaml(Path(path))
    merged = {**_DEFAULT_PARAMS, **cfg}
    _PARAMS = merged
    return merged


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


def detect_mode_simple(features: dict) -> str:
    """Return trade mode using the regime preclassifier only."""
    regime = classify_regime(features)
    return {"trend": "trend_follow", "range": "scalp_momentum"}.get(regime, "no_trade")


def detect_mode(ctx: MarketContext) -> str:
    """Return trade mode from rule-based numeric thresholds."""
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

    return "scalp_momentum"


def _norm(value: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    v = abs(value) / scale
    return min(max(v, 0.0), 1.0)


def select_mode(ctx: Dict[str, float], snapshot: Any | None = None) -> str:
    """Return trading mode blending numeric and LLM scores."""
    cfg = _PARAMS or load_config()
    trend_th = float(cfg.get("TREND_STR_THLD", 0.7))
    range_th = float(cfg.get("RANGE_SCORE_THLD", 0.7))

    slope = float(ctx.get("ema_slope_15m", 0.0))
    adx = float(ctx.get("adx_15m", 0.0))
    overshoot = bool(ctx.get("overshoot_flag"))

    trend_strength = _norm(adx, 50.0) * _norm(slope, 0.3)

    stddev_pct = float(ctx.get("stddev_pct_15m", 0.0))
    ema12 = float(ctx.get("ema12_15m", 0.0))
    ema26 = float(ctx.get("ema26_15m", 0.0))
    atr = float(ctx.get("atr_15m", 0.0))
    diff_ratio = abs(ema12 - ema26) / atr if atr else 0.0
    range_score = (1 - stddev_pct) * (1 - diff_ratio)

    if snapshot is not None:
        llm_scores = get_mode_scores(snapshot)
        numeric = {
            "TREND": trend_strength,
            "BASE_SCALP": range_score,
            "REBOUND_SCALP": 1.0 if overshoot else 0.0,
        }
        blended = {
            k: 0.6 * numeric[k] + 0.4 * float(llm_scores.get(k, 0.0))
            for k in numeric
        }
        return max(blended, key=blended.get)

    if overshoot:
        return "REBOUND_SCALP"
    if trend_strength > trend_th:
        return "TREND"
    if range_score > range_th:
        return "BASE_SCALP"
    return "BASE_SCALP"


__all__ = [
    "MarketContext",
    "detect_mode",
    "detect_mode_simple",
    "load_config",
    "select_mode",
]
