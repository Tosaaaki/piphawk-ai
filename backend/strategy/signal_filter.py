# backend/strategy/signal_filter.py
"""
軽量シグナル・フィルター

JobRunner や Strategy 層が AI を呼び出す前に
「テクニカル指標が最低限の条件を満たしているか」を判定する。
環境変数でしきい値を調整できるようにしておくことで、
strategy_analyzer から自動チューニングが可能。
"""

import datetime
import logging
import math
from collections import deque
from datetime import timezone

import pandas as pd

from backend.indicators.adx import calculate_adx_slope
from backend.market_data.tick_fetcher import fetch_tick_data
from backend.strategy.higher_tf_analysis import analyze_higher_tf
from backend.utils import env_loader
from filters.market_filters import _in_trade_hours

logger = logging.getLogger(__name__)

REVERSAL_RSI_DIFF = float(env_loader.get_env("REVERSAL_RSI_DIFF", "15"))
# スキャル専用の厳格判定フラグ
SCALP_STRICT_FILTER = (
    env_loader.get_env("SCALP_STRICT_FILTER", "false").lower() == "true"
)

# Overshoot 評価用の直近ローソク足高値・安値を保持
_WINDOW_LEN = int(env_loader.get_env("OVERSHOOT_WINDOW_CANDLES", "0"))
_recent_highs: deque[float] = deque(maxlen=_WINDOW_LEN) if _WINDOW_LEN > 0 else deque()
_recent_lows: deque[float] = deque(maxlen=_WINDOW_LEN) if _WINDOW_LEN > 0 else deque()

# Overshoot 検出時刻を保持し、時間経過でしきい値を緩和する
_last_overshoot_ts: datetime.datetime | None = None


def update_overshoot_window(high: float, low: float) -> None:
    """Add latest candle high/low to the deque."""
    if _WINDOW_LEN <= 0:
        return
    try:
        _recent_highs.append(float(high))
        _recent_lows.append(float(low))
    except Exception:
        pass


def _ema_direction(fast, slow) -> str | None:
    """Return EMA-based direction."""
    try:
        f = float(fast.iloc[-1]) if hasattr(fast, "iloc") else float(fast[-1])
        s = float(slow.iloc[-1]) if hasattr(slow, "iloc") else float(slow[-1])
    except Exception:
        return None
    if f > s:
        return "long"
    if f < s:
        return "short"
    return None


def counter_trend_block(
    side: str,
    ind_m5: dict,
    ind_m15: dict | None = None,
    ind_h1: dict | None = None,
) -> bool:
    """Return True when higher timeframe trend opposes the side."""
    if side not in ("long", "short"):
        return False
    dir_m15 = (
        _ema_direction(ind_m15.get("ema_fast"), ind_m15.get("ema_slow"))
        if ind_m15
        else None
    )
    dir_h1 = (
        _ema_direction(ind_h1.get("ema_fast"), ind_h1.get("ema_slow"))
        if ind_h1
        else None
    )
    if dir_m15 and dir_h1 and dir_m15 == dir_h1 and side != dir_m15:
        adx_override = float(env_loader.get_env("COUNTER_BYPASS_ADX", "0"))
        adx_series = ind_m5.get("adx")
        dir_m5 = _ema_direction(ind_m5.get("ema_fast"), ind_m5.get("ema_slow"))
        try:
            if (
                adx_override > 0
                and adx_series is not None
                and len(adx_series) >= 1
                and dir_m5 == side
                and float(
                    adx_series.iloc[-1]
                    if hasattr(adx_series, "iloc")
                    else adx_series[-1]
                )
                >= adx_override
            ):
                return False
        except Exception:
            pass
        return True
    adx_thresh = float(env_loader.get_env("BLOCK_ADX_MIN", "25"))
    adx_series = ind_m5.get("adx")
    try:
        if adx_series is not None and len(adx_series) >= 2:
            prev_val = (
                float(adx_series.iloc[-2])
                if hasattr(adx_series, "iloc")
                else float(adx_series[-2])
            )
            cur_val = (
                float(adx_series.iloc[-1])
                if hasattr(adx_series, "iloc")
                else float(adx_series[-1])
            )
            dir_m5 = _ema_direction(ind_m5.get("ema_fast"), ind_m5.get("ema_slow"))
            if (
                cur_val >= adx_thresh
                and cur_val > prev_val
                and dir_m5
                and side != dir_m5
            ):
                return True
            # 強い下降トレンド時のロング抑制
            if side == "long" and dir_m5 == "short" and cur_val >= adx_thresh:
                return True
            # 強い上昇トレンド時のショート抑制
            if side == "short" and dir_m5 == "long" and cur_val >= adx_thresh:
                return True
    except Exception:
        pass
    return False


def detect_climax_reversal(
    candles: list[dict],
    indicators: dict,
    *,
    lookback: int = 50,
    z_thresh: float | None = None,
) -> str | None:
    """Return reversal side when BB±2σ breach and ATR z-score exceeds threshold."""
    if env_loader.get_env("CLIMAX_ENABLED", "true").lower() != "true":
        return None
    if z_thresh is None:
        z_thresh = float(env_loader.get_env("CLIMAX_ZSCORE", "1.5"))
    if not candles:
        return None
    try:
        close = float(candles[-1]["mid"]["c"])
    except Exception:
        return None
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    if bb_upper is None or bb_lower is None or not len(bb_upper):
        return None
    up = float(bb_upper.iloc[-1]) if hasattr(bb_upper, "iloc") else float(bb_upper[-1])
    low = float(bb_lower.iloc[-1]) if hasattr(bb_lower, "iloc") else float(bb_lower[-1])
    side = None
    if close > up:
        side = "short"
    elif close < low:
        side = "long"
    else:
        return None
    atr_series = indicators.get("atr")
    if atr_series is None or len(atr_series) < lookback:
        return None
    if hasattr(atr_series, "iloc"):
        vals = [float(v) for v in atr_series.iloc[-lookback:]]
        cur = float(atr_series.iloc[-1])
    else:
        vals = [float(v) for v in atr_series[-lookback:]]
        cur = float(atr_series[-1])
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = math.sqrt(var)
    if std == 0:
        return None
    z = (cur - mean) / std
    if z > z_thresh:
        return side
    return None


# ────────────────────────────────────────────────
#  簡易ピーク反転検出
# ────────────────────────────────────────────────
def detect_peak_reversal(candles: list[dict], side: str) -> bool:
    """最後の3本で中央が高値(安値)となり、最終足が反対方向へ引けたらTrue"""

    if len(candles) < 3:
        return False
    try:
        sub = candles[-3:]
        highs = [float(c.get("mid", c).get("h")) for c in sub]
        lows = [float(c.get("mid", c).get("l")) for c in sub]
        closes = [float(c.get("mid", c).get("c")) for c in sub]
    except Exception:
        return False

    if side == "long":
        return highs[1] >= highs[0] and highs[1] >= highs[2] and closes[2] < closes[1]
    elif side == "short":
        return lows[1] <= lows[0] and lows[1] <= lows[2] and closes[2] > closes[1]
    return False


def consecutive_lower_lows(candles: list[dict], count: int = 3) -> bool:
    """Return True if there are ``count`` consecutive lower lows."""
    if len(candles) < count + 1:
        return False
    try:
        lows = [float(c.get("mid", c).get("l")) for c in candles[-(count + 1) :]]
    except Exception:
        return False
    return all(lows[i] < lows[i - 1] for i in range(1, len(lows)))


def consecutive_higher_highs(candles: list[dict], count: int = 3) -> bool:
    """Return True if there are ``count`` consecutive higher highs."""
    if len(candles) < count + 1:
        return False
    try:
        highs = [float(c.get("mid", c).get("h")) for c in candles[-(count + 1) :]]
    except Exception:
        return False
    return all(highs[i] > highs[i - 1] for i in range(1, len(highs)))


def consecutive_lower_highs(candles: list[dict], count: int = 3) -> bool:
    """Return True if there are ``count`` consecutive lower highs."""
    if len(candles) < count + 1:
        return False
    try:
        highs = [float(c.get("mid", c).get("h")) for c in candles[-(count + 1) :]]
    except Exception:
        return False
    return all(highs[i] < highs[i - 1] for i in range(1, len(highs)))


# ────────────────────────────────────────────────
#  Trend追随前フィルター
# ────────────────────────────────────────────────
def filter_pre_ai(
    candles: list[dict], indicators: dict, market_cond: dict | None = None
) -> bool:
    """Return True when the last candle is a large trend bar.

    The function checks the body length of the most recent candle and
    compares it with the current ATR value. When the candle body exceeds
    ``1.5 × ATR`` and its direction matches ``market_cond['trend_direction']``
    we skip the AI entry decision.
    """

    try:
        if not candles:
            return False
        last = candles[-1]
        if "mid" in last:
            o_val = float(last["mid"].get("o", 0))
            c_val = float(last["mid"].get("c", 0))
        else:
            o_val = float(last.get("o", 0))
            c_val = float(last.get("c", 0))
        body_len = c_val - o_val

        atr_series = indicators.get("atr")
        if atr_series is None or len(atr_series) == 0:
            return False
        atr = (
            float(atr_series.iloc[-1])
            if hasattr(atr_series, "iloc")
            else float(atr_series[-1])
        )

        follow_trend = None
        if market_cond is not None:
            follow_trend = market_cond.get("trend_direction")

        side = "long" if body_len > 0 else "short"

        skip_entry = abs(body_len) > 1.5 * atr and side == follow_trend
        return bool(skip_entry)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"filter_pre_ai failed: {exc}")
        return False


# ────────────────────────────────────────────────
#  EMA helper for exit‑filter
# ────────────────────────────────────────────────
def _ema_flat_or_cross(
    fast: pd.Series, slow: pd.Series, side: str, pip_size: float = 0.01
) -> bool:
    """
    True if ‑ for the given side ‑ the last 2 candles both moved
    against the position *or* fast / slow EMA are virtually overlapped.
    pip_size × 2 以内の乖離を「フラット」とみなす。
    """
    if len(fast) < 2 or len(slow) < 2:
        return False
    latest_fast, prev_fast = fast.iloc[-1], fast.iloc[-2]
    latest_slow, prev_slow = slow.iloc[-1], slow.iloc[-2]

    overlap = abs(latest_fast - latest_slow) <= pip_size * 2

    if side == "long":
        two_bars_below = latest_fast < latest_slow and prev_fast < prev_slow
        return two_bars_below or overlap
    elif side == "short":
        two_bars_above = latest_fast > latest_slow and prev_fast > prev_slow
        return two_bars_above or overlap
    return False


# ────────────────────────────────────────────────
#  エントリー用フィルター
#     indicators   : calculate_indicators() が返す dict
#  戻り値 True  → AI へ問い合わせる
#        False → スキップ
# ────────────────────────────────────────────────
def _rsi_cross_up_or_down(series: pd.Series, *, lookback: int = 1) -> bool:
    """Return True when RSI crosses up from <30 to ≥35 or down from >70 to ≤65.

    Parameters
    ----------
    series : pandas.Series
        RSI series ordered oldest → newest.
    lookback : int, default 1
        How many candles back to search for the opposite state.
        ``lookback=1`` reproduces the previous behaviour where only the
        immediately preceding candle is inspected.
    """
    try:
        length = len(series)
    except Exception:
        length = len(getattr(series, "_data", []))

    if length < lookback + 1:
        return False

    latest = series.iloc[-1] if hasattr(series, "iloc") else series[-1]
    try:
        latest_f = float(latest)
    except Exception:
        return False

    prev_values = (
        series.iloc[-(lookback + 1) : -1]
        if hasattr(series, "iloc")
        else series[-(lookback + 1) : -1]
    )
    try:
        crossed_up = any(float(p) < 30 for p in prev_values) and latest_f >= 35
        crossed_down = any(float(p) > 70 for p in prev_values) and latest_f <= 65
        return crossed_up or crossed_down
    except Exception:
        return False


def rapid_reversal_block(
    rsi_m5: pd.Series, rsi_m15: pd.Series, macd_hist: pd.Series
) -> bool:
    """Return True when RSI divergence and MACD histogram suggest a sharp reversal."""

    try:
        diff = float(rsi_m5.iloc[-1]) - float(rsi_m15.iloc[-1])
    except Exception:
        return False

    try:
        hist = float(macd_hist.iloc[-1])
    except Exception:
        return False

    if diff >= REVERSAL_RSI_DIFF and hist > 0:
        return True
    if diff <= -REVERSAL_RSI_DIFF and hist < 0:
        return True
    return False


def pass_entry_filter(
    indicators: dict,
    price: float | None = None,
    indicators_m1: dict | None = None,
    indicators_m15: dict | None = None,
    indicators_h1: dict | None = None,
    *,
    mode: str | None = None,
    context: dict | None = None,
) -> bool:
    """Simplified entry filter.

    Filters only when the market is closed or during the configured quiet hours.
    The overshoot check is preserved to update ``context`` but never blocks the
    entry.
    """

    global _last_overshoot_ts

    if context is None:
        context = {}

    # DISABLE_ENTRY_FILTER が true ならフィルターを無効化
    if env_loader.get_env("DISABLE_ENTRY_FILTER", "false").lower() == "true":
        return True

    # エントリーフィルターは市場休場中や禁止時間のみブロックする

    quiet_start = float(env_loader.get_env("QUIET_START_HOUR_JST", "3"))
    quiet_end = float(env_loader.get_env("QUIET_END_HOUR_JST", "7"))
    quiet2_enabled = env_loader.get_env("QUIET2_ENABLED", "false").lower() == "true"
    if quiet2_enabled:
        quiet2_start = float(env_loader.get_env("QUIET2_START_HOUR_JST", "23"))
        quiet2_end = float(env_loader.get_env("QUIET2_END_HOUR_JST", "1"))
    else:
        quiet2_start = quiet2_end = None

    now_jst = datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=9)
    current_time = now_jst.hour + now_jst.minute / 60.0

    def _in_range(start: float | None, end: float | None) -> bool:
        if start is None or end is None:
            return False
        return (
            (start < end and start <= current_time < end)
            or (start > end and (current_time >= start or current_time < end))
            or (start == end)
        )

    if _in_range(quiet_start, quiet_end) or _in_range(quiet2_start, quiet2_end):
        logger.info("Filter NG: session")
        q2_msg = f" or {quiet2_start}-{quiet2_end}" if quiet2_enabled else ""
        logger.debug(
            f"EntryFilter blocked by quiet hours ({quiet_start}-{quiet_end}{q2_msg})"
        )
        context["reason"] = "session"
        return False

    if not _in_trade_hours():
        logger.info("Filter NG: market_closed")
        context["reason"] = "market_closed"
        return False

    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    atr_series = indicators.get("atr")
    width_ratio = 0.0
    if (
        bb_upper is not None
        and bb_lower is not None
        and len(bb_upper)
        and len(bb_lower)
        and atr_series is not None
        and len(atr_series)
    ):
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
        bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
        width_ratio = (bw_pips - bw_thresh) / bw_thresh if bw_thresh != 0 else 0.0
        overshoot_mult = float(env_loader.get_env("OVERSHOOT_ATR_MULT", "1.0"))
        dyn_coeff = float(env_loader.get_env("OVERSHOOT_DYNAMIC_COEFF", "0"))
        base_mult = float(env_loader.get_env("OVERSHOOT_BASE_MULT", str(overshoot_mult)))
        max_mult = float(env_loader.get_env("OVERSHOOT_MAX_MULT", "0.7"))
        recover_rate = float(env_loader.get_env("OVERSHOOT_RECOVERY_RATE", "0.05"))
        elapsed_min = 0.0
        if _last_overshoot_ts is not None:
            elapsed_min = (
                datetime.datetime.now(timezone.utc) - _last_overshoot_ts
            ).total_seconds() / 60.0
        dynamic_base = min(max_mult, base_mult + recover_rate * elapsed_min)
        dynamic_mult = dynamic_base * (1 + dyn_coeff * width_ratio)
        threshold = bb_lower.iloc[-1] - atr_series.iloc[-1] * dynamic_mult
        if price is not None and price <= threshold:
            _last_overshoot_ts = datetime.datetime.now(timezone.utc)
            context["overshoot_flag"] = True
            logger.info("Overshoot detected: flagging rebound opportunity")
        else:
            context.setdefault("overshoot_flag", False)
        dynamic = env_loader.get_env("OVERSHOOT_DYNAMIC", "false").lower() == "true"
        max_pips = float(env_loader.get_env("OVERSHOOT_MAX_PIPS", "0"))
        if dynamic:
            factor = float(env_loader.get_env("OVERSHOOT_FACTOR", "0.5"))
            floor = float(env_loader.get_env("OVERSHOOT_FLOOR", "1.0"))
            ceil = float(env_loader.get_env("OVERSHOOT_CEIL", "20.0"))
            atr_pips = atr_series.iloc[-1] / pip_size
            max_pips = min(max(atr_pips * factor, floor), ceil)
        threshold_atr = bb_lower.iloc[-1] - atr_series.iloc[-1] * overshoot_mult
        threshold_pips = bb_lower.iloc[-1] - max_pips * pip_size if max_pips else None
        over = False
        if price is not None:
            if overshoot_mult > 0 and price <= threshold_atr:
                over = True
            if threshold_pips is not None and price <= threshold_pips:
                over = True
        if over:
            context["overshoot_flag"] = True
            if env_loader.get_env("OVERSHOOT_MODE", "block").lower() != "warn":
                logger.warning("Overshoot detected; entry allowed but flagged")
        if _WINDOW_LEN > 1 and len(_recent_highs) >= _WINDOW_LEN:
            high = max(_recent_highs)
            low = min(_recent_lows)
            range_pips = (high - low) / pip_size
            limit_pips = float(env_loader.get_env("OVERSHOOT_MAX_PIPS", "0"))
            if dynamic:
                factor = float(env_loader.get_env("OVERSHOOT_FACTOR", "0.5"))
                floor = float(env_loader.get_env("OVERSHOOT_FLOOR", "1.0"))
                ceil = float(env_loader.get_env("OVERSHOOT_CEIL", "20.0"))
                atr_pips = atr_series.iloc[-1] / pip_size
                limit_pips = min(max(atr_pips * factor, floor), ceil)
            atr_limit_pips = atr_series.iloc[-1] * dynamic_mult / pip_size
            if (limit_pips and range_pips > limit_pips) or range_pips > atr_limit_pips:
                _last_overshoot_ts = datetime.datetime.now(timezone.utc)
                context["overshoot_flag"] = True
                logger.info("Overshoot range detected: flag set")

    return True


# ────────────────────────────────────────────────
#  エグジット用フィルター（必要なら後で拡張）
# ────────────────────────────────────────────────
def pass_exit_filter(indicators: dict, position_side: str) -> bool:
    # --- Test override: set DISABLE_EXIT_FILTER=true in .env to bypass all exit filters
    if env_loader.get_env("DISABLE_EXIT_FILTER", "false").lower() == "true":
        return True
    """
    Exit‑side filter

    We only query the AI for an exit when the market has calmed down
    (ATR が十分小さい) *and* the RSI has reverted to a neutral zone.
    そうでないときは、まだトレンド継続中とみなしてスキップする。

    Env‑tunable thresholds
    ----------------------
    RSI_EXIT_LOWER : lower bound of the neutral RSI zone (default 40)
    RSI_EXIT_UPPER : upper bound of the neutral RSI zone (default 60)
    ATR_EXIT_THRESHOLD : maximum ATR allowed to regard the market as “calm” (default 0.04)
    """
    rsi_series = indicators["rsi"]
    atr_series = indicators["atr"]

    # 最新値を安全に取得
    latest_rsi = rsi_series.iloc[-1] if len(rsi_series) else None
    latest_atr = atr_series.iloc[-1] if len(atr_series) else None
    if latest_rsi is None or latest_atr is None:
        # データが揃っていないときは AI に任せる
        return True

    lower = float(env_loader.get_env("RSI_EXIT_LOWER", "35"))
    upper = float(env_loader.get_env("RSI_EXIT_UPPER", "65"))
    atr_th = float(env_loader.get_env("ATR_EXIT_THRESHOLD", "0.04"))

    in_neutral_band = lower <= latest_rsi <= upper
    atr_is_calm = latest_atr <= atr_th

    ema_fast = indicators["ema_fast"]
    ema_slow = indicators["ema_slow"]

    latest_ema_fast = ema_fast.iloc[-1] if len(ema_fast) else None
    latest_ema_slow = ema_slow.iloc[-1] if len(ema_slow) else None
    prev_ema_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else None
    prev_ema_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else None

    if None in [latest_ema_fast, latest_ema_slow, prev_ema_fast, prev_ema_slow]:
        return True

    ema_cross_up = prev_ema_fast < prev_ema_slow and latest_ema_fast > latest_ema_slow
    ema_cross_down = prev_ema_fast > prev_ema_slow and latest_ema_fast < latest_ema_slow

    if position_side == "long":
        cross_signal = ema_cross_down
    elif position_side == "short":
        cross_signal = ema_cross_up
    else:
        cross_signal = False

    # fast / slow EMA がほぼ重なった、または 2 本連続で逆方向なら勢い喪失と判断
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    flat_or_cross = _ema_flat_or_cross(ema_fast, ema_slow, position_side, pip_size)

    return (in_neutral_band and atr_is_calm) or cross_signal or flat_or_cross
