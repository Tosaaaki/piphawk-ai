from __future__ import annotations

"""Mode selection logic v2."""

from pathlib import Path
from typing import Dict

import yaml

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "mode_thresholds.yml"
_THRESHOLDS: dict | None = None


def _load_thresholds() -> dict:
    global _THRESHOLDS
    if _THRESHOLDS is None:
        try:
            with _DEFAULT_PATH.open("r", encoding="utf-8") as f:
                _THRESHOLDS = yaml.safe_load(f) or {}
        except Exception:
            _THRESHOLDS = {}
    return _THRESHOLDS


def _norm(value: float, scale: float) -> float:
    """Normalize value to 0-1."""
    if scale <= 0:
        return 0.0
    v = abs(value) / scale
    return min(max(v, 0.0), 1.0)


def select_mode(ctx: Dict[str, float]) -> str:
    """Return trading mode from context."""
    cfg = _load_thresholds()
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

    if overshoot:
        return "REBOUND_SCALP"
    if trend_strength > trend_th:
        return "TREND"
    if range_score > range_th:
        return "BASE_SCALP"
    return "BASE_SCALP"

__all__ = ["select_mode"]
