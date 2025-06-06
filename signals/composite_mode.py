from __future__ import annotations
"""Composite trade mode decision utility."""

from typing import Sequence, Iterable
from indicators.candlestick import detect_upper_wick_cluster
import logging

from backend.utils import env_loader
from .mode_params import get_params

MODE_PARAMS = get_params()
WEIGHTS = MODE_PARAMS.get("weights", {})
VOL_LEVELS = MODE_PARAMS.get("volatility_levels", {})
SCALP_PARAMS = MODE_PARAMS.get("scalp", {})
HYSTERESIS = MODE_PARAMS.get("hysteresis", {"trend": 3, "scalp": 3})
TREND_SCORE_MIN_CFG = int(MODE_PARAMS.get("trend_score_min", 3))
SCALP_SCORE_MAX_CFG = int(MODE_PARAMS.get("scalp_score_max", -1))
EMA_SLOPE_THRESH = MODE_PARAMS.get("ema_slope", {"mild": 0.05, "strong": 0.15})

MODE_ATR_PIPS_MIN = float(env_loader.get_env("MODE_ATR_PIPS_MIN", "5"))
MODE_BBWIDTH_PIPS_MIN = float(env_loader.get_env("MODE_BBWIDTH_PIPS_MIN", "3"))
MODE_EMA_SLOPE_MIN = float(env_loader.get_env("MODE_EMA_SLOPE_MIN", "0.1"))
MODE_ADX_MIN = float(env_loader.get_env("MODE_ADX_MIN", "25"))
MODE_VOL_MA_MIN = float(env_loader.get_env("MODE_VOL_MA_MIN", env_loader.get_env("MIN_VOL_MA", "80")))
VOL_MA_PERIOD = int(env_loader.get_env("VOL_MA_PERIOD", "5"))

# --- Additional scoring parameters -------------------------------------
MODE_TREND_SCORE_MIN = int(env_loader.get_env("MODE_TREND_SCORE_MIN", "4"))
MODE_ADX_STRONG = float(env_loader.get_env("MODE_ADX_STRONG", "40"))
MODE_DI_DIFF_MIN = float(env_loader.get_env("MODE_DI_DIFF_MIN", "10"))
MODE_DI_DIFF_STRONG = float(env_loader.get_env("MODE_DI_DIFF_STRONG", "25"))
MODE_EMA_SLOPE_STRONG = float(env_loader.get_env("MODE_EMA_SLOPE_STRONG", "0.3"))
MODE_VOL_RATIO_MIN = float(env_loader.get_env("MODE_VOL_RATIO_MIN", "1"))
MODE_VOL_RATIO_STRONG = float(env_loader.get_env("MODE_VOL_RATIO_STRONG", "2"))
MODE_BONUS_START_JST = float(env_loader.get_env("MODE_BONUS_START_JST", "16"))
MODE_BONUS_END_JST = float(env_loader.get_env("MODE_BONUS_END_JST", "1"))
MODE_PENALTY_START_JST = float(env_loader.get_env("MODE_PENALTY_START_JST", "2"))
MODE_PENALTY_END_JST = float(env_loader.get_env("MODE_PENALTY_END_JST", "8"))
MODE_LOG_PATH = env_loader.get_env("MODE_LOG_PATH", "analysis/trade_mode_log.csv")
MODE_ATR_QTL = float(env_loader.get_env("MODE_ATR_QTL", "0"))
MODE_ADX_QTL = float(env_loader.get_env("MODE_ADX_QTL", "0"))
MODE_QTL_LOOKBACK = int(env_loader.get_env("MODE_QTL_LOOKBACK", "20"))
HTF_SLOPE_MIN = float(env_loader.get_env("HTF_SLOPE_MIN", "0.1"))

# --- Vol-Trend matrix parameters ------------------------------------
ATR_HIGH_RATIO = float(env_loader.get_env("ATR_HIGH_RATIO", "1.4"))
ATR_LOW_RATIO = float(env_loader.get_env("ATR_LOW_RATIO", "0.8"))
ADX_TREND_THR = float(env_loader.get_env("ADX_TREND_THR", "25"))
ADX_FLAT_THR = float(env_loader.get_env("ADX_FLAT_THR", "17"))

# 高ATRかつADX低下時のスキャルプ判定用閾値
HIGH_ATR_PIPS = float(env_loader.get_env("HIGH_ATR_PIPS", "10"))
LOW_ADX_THRESH = float(env_loader.get_env("LOW_ADX_THRESH", "20"))


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


def _vol_level(atr_pct: float | None) -> str:
    if atr_pct is None:
        return "normal"
    if atr_pct < 33:
        return "low"
    if atr_pct > 66:
        return "high"
    return "normal"


_LAST_MODE: str | None = None
_LAST_SWITCH: int = 0


def _in_window(now: float, start: float, end: float) -> bool:
    """Return True if ``now`` hour is within start-end range (JST)."""
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def decide_trade_mode_matrix(
    atr: float,
    atr_base: float,
    adx: float,
    atr_high_thr: float = ATR_HIGH_RATIO,
    atr_low_thr: float = ATR_LOW_RATIO,
    adx_trend_thr: float = ADX_TREND_THR,
    adx_flat_thr: float = ADX_FLAT_THR,
) -> str:
    """Return mode based on volatility and trend strength."""
    if atr_base <= 0:
        return "flat"
    atr_ratio = atr / atr_base
    if atr_ratio >= atr_high_thr and adx <= adx_flat_thr:
        return "scalp_range"
    if atr_ratio >= atr_high_thr and adx >= adx_trend_thr:
        return "scalp_momentum"
    if atr_ratio <= atr_low_thr and adx >= adx_trend_thr:
        return "trend_follow"
    return "flat"
def _quantile(data: Iterable, q: float) -> float | None:
    """Return q-th quantile from sequence ``data``."""
    try:
        vals = [float(v) for v in data if v is not None]
    except Exception:
        return None
    if not vals:
        return None
    vals.sort()
    k = (len(vals) - 1) * q
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[int(k)]
    return vals[f] * (c - k) + vals[c] * (k - f)


def decide_trade_mode_detail(
    indicators: dict, candles: Sequence[dict] | None = None
) -> tuple[str, int, list[str]]:
    """Return mode, score and reasons for the given indicators."""
    m5 = indicators
    m1 = indicators.get("M1", {})
    s10 = indicators.get("S10", {})

    atr_pct_m5 = _last(m5.get("atr_pct"))
    level = _vol_level(atr_pct_m5)
    thr = VOL_LEVELS.get(level, VOL_LEVELS.get("normal", {}))

    adx_m5 = _last(m5.get("adx"))
    adx_m1 = _last(m1.get("adx"))
    atr_pct_m1 = _last(m1.get("atr_pct"))
    adx_s10 = _last(s10.get("adx"))
    atr_pct_s10 = _last(s10.get("atr_pct"))
    ema_slope = _last(m5.get("ema_slope"))

    score = 0
    reasons: list[str] = []

    if adx_m5 is not None and adx_m5 >= thr.get("adx_m5_min", MODE_ADX_MIN):
        score += 2 * float(WEIGHTS.get("adx_m5", 1))
        reasons.append(f"ADX_M5 {adx_m5:.1f}")
    if atr_pct_m5 is not None and atr_pct_m5 >= thr.get("atr_pct_m5_min", 0.004):
        score += float(WEIGHTS.get("atr_pct_m5", 1))
        reasons.append(f"ATR%M5 {atr_pct_m5:.4f}")
    if adx_m1 is not None and adx_m1 >= thr.get("adx_m1_min", 20):
        score += float(WEIGHTS.get("adx_m1", 1))
        reasons.append(f"ADX_M1 {adx_m1:.1f}")
    if atr_pct_m1 is not None and atr_pct_m1 >= thr.get("atr_pct_m1_min", 0.0025):
        score += float(WEIGHTS.get("atr_pct_m1", 1))
        reasons.append(f"ATR%M1 {atr_pct_m1:.4f}")

    if adx_m5 is not None and adx_m5 <= SCALP_PARAMS.get("adx_m5_max", 15):
        score -= 2
    if atr_pct_m5 is not None and atr_pct_m5 <= SCALP_PARAMS.get("atr_pct_m5_max", 0.0025):
        score -= 1
    if adx_m1 is not None and adx_m1 <= SCALP_PARAMS.get("adx_m1_max", 12):
        score -= 1

    if candles is not None and len(candles) >= 3:
        try:
            bodies = [abs(float(c["mid"]["c"]) - float(c["mid"]["o"])) for c in candles[-3:]]
            widths = [float(c["mid"]["h"]) - float(c["mid"]["l"]) for c in candles[-3:]]
            ratio = sum(bodies) / sum(widths) if sum(widths) else 1
            if ratio <= SCALP_PARAMS.get("body_shrink_ratio", 0.35):
                score -= 1
        except Exception:
            pass

    if adx_s10 is not None and atr_pct_s10 is not None:
        if adx_s10 > SCALP_PARAMS.get("s10_adx_min", 20) and atr_pct_s10 >= SCALP_PARAMS.get("s10_atr_pct_min", 0.001):
            score -= 1

    if ema_slope is not None:
        sabs = abs(ema_slope)
        if sabs >= EMA_SLOPE_THRESH.get("strong", 0.15):
            score += float(WEIGHTS.get("ema_slope_strong", 2))
        elif sabs >= EMA_SLOPE_THRESH.get("mild", 0.05):
            score += float(WEIGHTS.get("ema_slope_base", 1))
        reasons.append(f"EMA {sabs:.2f}")

    global _LAST_MODE, _LAST_SWITCH
    candle_len = len(candles) if candles else 0
    if _LAST_MODE and candle_len - _LAST_SWITCH < HYSTERESIS.get(_LAST_MODE.split("_")[0], 3):
        return _LAST_MODE, score, reasons

    if score >= TREND_SCORE_MIN_CFG:
        mode = "trend_follow"
    elif score <= SCALP_SCORE_MAX_CFG:
        mode = "scalp_momentum"
    else:
        mode = "flat"

    if mode != _LAST_MODE:
        _LAST_MODE = mode
        _LAST_SWITCH = candle_len

    logging.getLogger(__name__).info("decide_trade_mode -> %s (score=%d)", mode, score)
    return mode, score, reasons


def decide_trade_mode(indicators: dict) -> str:
    """Return trade mode based on scoring approach."""
    mode, _score, _reasons = decide_trade_mode_detail(indicators)
    return mode


__all__ = [
    "decide_trade_mode",
    "decide_trade_mode_detail",
    "decide_trade_mode_matrix",
    "MODE_ATR_PIPS_MIN",
    "MODE_BBWIDTH_PIPS_MIN",
    "MODE_EMA_SLOPE_MIN",
    "MODE_ADX_MIN",
    "MODE_VOL_MA_MIN",
    "MODE_TREND_SCORE_MIN",
    "MODE_ADX_STRONG",
    "MODE_DI_DIFF_MIN",
    "MODE_DI_DIFF_STRONG",
    "MODE_EMA_SLOPE_STRONG",
    "MODE_VOL_RATIO_MIN",
    "MODE_VOL_RATIO_STRONG",
    "MODE_BONUS_START_JST",
    "MODE_BONUS_END_JST",
    "MODE_PENALTY_START_JST",
    "MODE_PENALTY_END_JST",
    "MODE_LOG_PATH",
    "HIGH_ATR_PIPS",
    "LOW_ADX_THRESH",
    "ATR_HIGH_RATIO",
    "ATR_LOW_RATIO",
    "ADX_TREND_THR",
    "ADX_FLAT_THR",
    "MODE_ATR_QTL",
    "MODE_ADX_QTL",
    "MODE_QTL_LOOKBACK",
    "HTF_SLOPE_MIN",
]
