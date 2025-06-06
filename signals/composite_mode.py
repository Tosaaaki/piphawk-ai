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


def decide_trade_mode_detail(indicators: dict) -> tuple[str, int, list[str]]:
    """Return mode, score and reasons for the given indicators."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    atr = _last(indicators.get("atr")) or 0.0
    bb_u = _last(indicators.get("bb_upper"))
    bb_l = _last(indicators.get("bb_lower"))
    bb_width_pips = 0.0
    if bb_u is not None and bb_l is not None:
        bb_width_pips = (float(bb_u) - float(bb_l)) / pip_size
    atr_pips = float(atr) / pip_size
    adx = _last(indicators.get("adx"))

    if adx is not None and atr_pips >= HIGH_ATR_PIPS and adx < LOW_ADX_THRESH:
        logging.getLogger(__name__).info(
            "decide_trade_mode: scalp override by ATR/ADX"
        )
        return "scalp", 0, [f"ATR {atr_pips:.1f}p", f"ADX {adx:.1f}"]

    atr_thresh = MODE_ATR_PIPS_MIN
    if MODE_ATR_QTL > 0:
        series = indicators.get("atr")
        if series is not None:
            if hasattr(series, "iloc"):
                recent = series.iloc[-MODE_QTL_LOOKBACK:]
            else:
                recent = series[-MODE_QTL_LOOKBACK:]
            qval = _quantile(recent, MODE_ATR_QTL)
            if qval is not None:
                atr_thresh = qval / pip_size

    adx_thresh = MODE_ADX_MIN

    score = 0
    reasons: list[str] = []

    # --- Volatility -----------------------------------------------------
    if atr_pips >= atr_thresh:
        score += 1
        reasons.append(f"ATR {atr_pips:.1f}p")
    if bb_width_pips >= MODE_BBWIDTH_PIPS_MIN:
        score += 1
        reasons.append(f"BB width {bb_width_pips:.1f}p")

    # --- Momentum -------------------------------------------------------
    ema_slope = _last(indicators.get("ema_slope"))
    macd_hist = _last(indicators.get("macd_hist"))
    adx = _last(indicators.get("adx"))
    plus_di = _last(indicators.get("plus_di"))
    minus_di = _last(indicators.get("minus_di"))

    if MODE_ADX_QTL > 0:
        adx_series = indicators.get("adx")
        if adx_series is not None:
            recent_adx = adx_series.iloc[-MODE_QTL_LOOKBACK:] if hasattr(adx_series, "iloc") else adx_series[-MODE_QTL_LOOKBACK:]
            q_adx = _quantile(recent_adx, MODE_ADX_QTL)
            if q_adx is not None:
                adx_thresh = q_adx
    if adx is not None:
        if adx >= MODE_ADX_STRONG:
            score += 2
        elif adx >= adx_thresh:
            score += 1
        reasons.append(f"ADX {adx:.1f}")

    if plus_di is not None and minus_di is not None:
        diff = abs(plus_di - minus_di)
        if diff >= MODE_DI_DIFF_STRONG:
            score += 2
        elif diff >= MODE_DI_DIFF_MIN:
            score += 1
        reasons.append(f"DI diff {diff:.1f}")

    if ema_slope is not None:
        sabs = abs(ema_slope)
        if sabs >= MODE_EMA_SLOPE_STRONG:
            score += 2
        elif sabs >= MODE_EMA_SLOPE_MIN:
            score += 1
        reasons.append(f"EMA slope {sabs:.2f}")

    if macd_hist is not None and abs(macd_hist) >= MODE_EMA_SLOPE_MIN:
        score += 1
        reasons.append("MACD hist")

    # --- Liquidity ------------------------------------------------------
    vol_series = indicators.get("volume")
    vol_ratio = None
    if vol_series is not None and len(vol_series) >= VOL_MA_PERIOD:
        if hasattr(vol_series, "iloc"):
            recent = vol_series.iloc[-VOL_MA_PERIOD:]
        else:
            recent = vol_series[-VOL_MA_PERIOD:]
        try:
            avg_vol = sum(float(v) for v in recent) / len(recent)
            vol_ratio = avg_vol / atr_pips if atr_pips else 0.0
            if vol_ratio >= MODE_VOL_RATIO_STRONG:
                score += 2
            elif vol_ratio >= MODE_VOL_RATIO_MIN:
                score += 1
            reasons.append(f"Vol ratio {vol_ratio:.1f}")
        except Exception:
            pass

    # --- Time bonus -----------------------------------------------------
    import datetime

    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    hour = now.hour + now.minute / 60.0
    if _in_window(hour, MODE_BONUS_START_JST, MODE_BONUS_END_JST):
        score += 1
    if _in_window(hour, MODE_PENALTY_START_JST, MODE_PENALTY_END_JST):
        score -= 1

    mode = "trend_follow" if score >= MODE_TREND_SCORE_MIN else "scalp"

    if mode == "trend_follow":
        h1_slope = _last(indicators.get("ema_slope_h1"))
        h4_slope = _last(indicators.get("ema_slope_h4"))
        slopes = [abs(s) for s in (h1_slope, h4_slope) if s is not None]
        if slopes and max(slopes) < HTF_SLOPE_MIN:
            mode = "scalp"
            reasons.append("HTF slope weak")

    # --- Logging --------------------------------------------------------
    try:
        import csv, os

        exists = os.path.exists(MODE_LOG_PATH)
        with open(MODE_LOG_PATH, "a", newline="") as f:
            fieldnames = [
                "timestamp",
                "atr_pips",
                "bb_width_pips",
                "ema_slope",
                "macd_hist",
                "adx",
                "di_diff",
                "vol_ratio",
                "hour_jst",
                "score",
                "mode",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not exists:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": now.isoformat(),
                    "atr_pips": atr_pips,
                    "bb_width_pips": bb_width_pips,
                    "ema_slope": ema_slope,
                    "macd_hist": macd_hist,
                    "adx": adx,
                    "di_diff": None if (plus_di is None or minus_di is None) else abs(plus_di - minus_di),
                    "vol_ratio": vol_ratio,
                    "hour_jst": hour,
                    "score": score,
                    "mode": mode,
                }
            )
    except Exception:
        logging.getLogger(__name__).debug("mode log failed", exc_info=True)

    logging.getLogger(__name__).info("decide_trade_mode -> %s (score=%d)", mode, score)
    return mode, score, reasons


def decide_trade_mode(indicators: dict) -> str:
    """Return trade mode based on ATR/ADX matrix."""
    atr_series = indicators.get("atr")
    adx_series = indicators.get("adx")
    atr = _last(atr_series) or 0.0
    adx = _last(adx_series) or 0.0
    atr_base = 0.0
    try:
        if atr_series is not None:
            length = min(len(atr_series), 150)
            if hasattr(atr_series, "iloc"):
                vals = atr_series.iloc[-length:]
            else:
                vals = atr_series[-length:]
            atr_base = sum(float(v) for v in vals) / length if length else 0.0
    except Exception:
        atr_base = 0.0
    return decide_trade_mode_matrix(atr, atr_base, adx)


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
