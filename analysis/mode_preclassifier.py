from __future__ import annotations

"""単純なADX/ATRベースの取引レジーム判定モジュール."""

from pathlib import Path

import yaml


def _last_val(series):
    """Return last value from list or pandas Series."""
    if series is None:
        return None
    try:
        if hasattr(series, "iloc"):
            if len(series):
                return float(series.iloc[-1])
            return None
        if isinstance(series, (list, tuple)):
            if series:
                return float(series[-1])
            return None
        return float(series)
    except Exception:
        return None

# 設定読み込み
_cfg: dict | None = None


def _load_cfg() -> dict:
    global _cfg
    if _cfg is None:
        path = Path(__file__).resolve().parents[1] / "config" / "strategy.yml"
        try:
            with path.open("r", encoding="utf-8") as f:
                _cfg = yaml.safe_load(f) or {}
        except Exception:
            _cfg = {}
    return _cfg


_cfg = _load_cfg()
_GRAY_BAND = tuple(float(x) for x in _cfg.get("GRAY_ADX_BAND", [25, 30]))


def classify_regime(features: dict) -> str:
    """ADX と ATR 指標から市場状態を分類する."""
    adx = _last_val(features.get("adx"))
    if adx is None:
        adx = 0.0
    atr_pct = _last_val(features.get("atr_pct"))
    if atr_pct is None:
        atr_pct = 0.0
    atr_percentile = _last_val(features.get("atr_percentile"))
    if atr_percentile is None:
        atr_percentile = 100.0

    if atr_percentile < 10:
        return "no_trade"
    if adx >= _GRAY_BAND[1]:
        return "trend"
    if adx <= _GRAY_BAND[0] - 5:
        return "range"
    return "gray"


__all__ = ["classify_regime"]
