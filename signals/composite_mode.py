from __future__ import annotations
"""Composite trade mode decision utility."""

from typing import Sequence, Iterable
from indicators.candlestick import detect_upper_wick_cluster
import logging
import datetime

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

# --- Hysteresis & mode score thresholds ------------------------------
TREND_ENTER_SCORE = float(env_loader.get_env("TREND_ENTER_SCORE", "0.66"))
SCALP_ENTER_SCORE = float(env_loader.get_env("SCALP_ENTER_SCORE", "0.33"))
TREND_HOLD_SCORE = float(env_loader.get_env("TREND_HOLD_SCORE", "0.50"))
SCALP_HOLD_SCORE = float(env_loader.get_env("SCALP_HOLD_SCORE", "0.30"))
MODE_STRONG_TREND_THRESH = float(env_loader.get_env("MODE_STRONG_TREND_THRESH", "0.9"))


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
) -> tuple[str, float, list[str]]:
    """Return mode, score and reasons for the given indicators."""

    m5 = indicators
    vols = m5.get("volume")
    if vols is None:
        vols = []
    elif hasattr(vols, "tolist"):
        vols = vols.tolist()
    vol_ma = sum(vols[-VOL_MA_PERIOD:]) / min(len(vols), VOL_MA_PERIOD) if vols else None

    atr_val = _last(m5.get("atr"))
    adx_vals = m5.get("adx")
    if adx_vals is None:
        adx_vals = []
    elif hasattr(adx_vals, "tolist"):
        adx_vals = adx_vals.tolist()
    adx_val = _last(adx_vals)

    plus_di = m5.get("plus_di")
    minus_di = m5.get("minus_di")
    di_diff = None
    p_val = _last(plus_di)
    m_val = _last(minus_di)
    if p_val is not None and m_val is not None:
        di_diff = abs(p_val - m_val)

    ema_val = _last(m5.get("ema_slope"))

    points = 0
    max_points = 0
    reasons: list[str] = []

    def _score_step(val: float | None, low: float, high: float, name: str) -> None:
        nonlocal points, max_points
        max_points += 2
        if val is None:
            reasons.append(f"{name} N/A")
            return
        if val >= high:
            points += 2
            reasons.append(f"{name} strong {val:.2f}")
        elif val >= low:
            points += 1
            reasons.append(f"{name} {val:.2f}")
        else:
            reasons.append(f"{name} weak {val:.2f}")

    _score_step(adx_val, MODE_ADX_MIN, MODE_ADX_STRONG, "ADX")
    _score_step(di_diff, MODE_DI_DIFF_MIN, MODE_DI_DIFF_STRONG, "DI diff")
    _score_step(abs(ema_val) if ema_val is not None else None, MODE_EMA_SLOPE_MIN, MODE_EMA_SLOPE_STRONG, "EMA slope")
    if vol_ma is not None:
        ratio = vol_ma / MODE_VOL_MA_MIN
    else:
        ratio = None
    _score_step(ratio, MODE_VOL_RATIO_MIN, MODE_VOL_RATIO_STRONG, "Volume")
    _score_step(atr_val, MODE_ATR_PIPS_MIN, MODE_ATR_PIPS_MIN * 2, "ATR")

    bonus = 0
    now_jst = datetime.datetime.utcnow().timestamp() + 9 * 3600
    hour = (now_jst % 86400) / 3600
    if _in_window(hour, MODE_BONUS_START_JST, MODE_BONUS_END_JST):
        bonus += 1
        reasons.append("session bonus")
    if _in_window(hour, MODE_PENALTY_START_JST, MODE_PENALTY_END_JST):
        bonus -= 1
        reasons.append("session penalty")

    score = (points + bonus) / max_points if max_points else 0.0
    score = max(0.0, min(1.0, score))

    body_shrink = False
    adx_drop = False
    if candles and len(candles) >= 2:
        try:
            b1 = abs(float(candles[-1]["mid"]["c"]) - float(candles[-1]["mid"]["o"]))
            b2 = abs(float(candles[-2]["mid"]["c"]) - float(candles[-2]["mid"]["o"]))
            body_shrink = b1 < b2
        except Exception:
            body_shrink = False
    if len(adx_vals) >= 2 and adx_vals[-1] < adx_vals[-2]:
        adx_drop = True

    if body_shrink and adx_drop:
        score -= 0.20

    global _LAST_MODE, _LAST_SWITCH
    candle_len = len(candles) if candles else 0

    strong_cond = (
        adx_val is not None
        and adx_val >= MODE_ADX_STRONG
        and di_diff is not None
        and di_diff >= MODE_DI_DIFF_STRONG
        and ema_val is not None
        and abs(ema_val) >= MODE_EMA_SLOPE_STRONG
    )

    if _LAST_MODE == "strong_trend" and strong_cond:
        mode = "strong_trend"
    elif strong_cond and score >= MODE_STRONG_TREND_THRESH:
        mode = "strong_trend"
    elif _LAST_MODE == "trend_follow" and score >= TREND_HOLD_SCORE:
        mode = "trend_follow"
    elif _LAST_MODE == "scalp_momentum" and score <= SCALP_HOLD_SCORE:
        mode = "scalp_momentum"
    elif score >= TREND_ENTER_SCORE:
        mode = "trend_follow"
    elif score <= SCALP_ENTER_SCORE:
        mode = "scalp_momentum"
    else:
        mode = _LAST_MODE or "flat"

    if mode != _LAST_MODE:
        _LAST_MODE = mode
        _LAST_SWITCH = candle_len

    logging.getLogger(__name__).info("decide_trade_mode -> %s (score=%.2f)", mode, score)
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
    "TREND_ENTER_SCORE",
    "SCALP_ENTER_SCORE",
    "TREND_HOLD_SCORE",
    "SCALP_HOLD_SCORE",
    "MODE_STRONG_TREND_THRESH",
]
