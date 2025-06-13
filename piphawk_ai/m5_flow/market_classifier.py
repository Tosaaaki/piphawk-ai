"""ADXとEMA乖離からレンジ/トレンドを判定する簡易クラスifier."""
from __future__ import annotations

from backend.utils import env_loader


def _last(series):
    if series is None:
        return None
    try:
        if hasattr(series, "iloc"):
            if len(series):
                return float(series.iloc[-1])
            return None
        if isinstance(series, (list, tuple)) and series:
            return float(series[-1])
    except Exception:
        return None
    return None


def classify_market(indicators: dict) -> str:
    """ADX値とEMA乖離でトレンド/レンジを返す."""
    adx = _last(indicators.get("adx"))
    ema_fast = _last(indicators.get("ema_fast"))
    ema_slow = _last(indicators.get("ema_slow"))
    if adx is None or ema_fast is None or ema_slow is None:
        return "range"

    pip = 0.01 if env_loader.get_env("DEFAULT_PAIR", "USD_JPY").endswith("_JPY") else 0.0001
    ema_diff = abs(ema_fast - ema_slow) / pip
    adx_thr = float(env_loader.get_env("M5_ADX_TREND_THR", "25"))
    diff_thr = float(env_loader.get_env("M5_EMA_DIFF_THR", "3"))
    if adx >= adx_thr and ema_diff >= diff_thr:
        return "trend"
    return "range"


__all__ = ["classify_market"]
