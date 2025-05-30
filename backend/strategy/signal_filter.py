# backend/strategy/signal_filter.py
"""
軽量シグナル・フィルター

JobRunner や Strategy 層が AI を呼び出す前に
「テクニカル指標が最低限の条件を満たしているか」を判定する。
環境変数でしきい値を調整できるようにしておくことで、
strategy_analyzer から自動チューニングが可能。
"""

import os
import math
import pandas as pd
import logging
import datetime
from backend.strategy.higher_tf_analysis import analyze_higher_tf
from backend.market_data.tick_fetcher import fetch_tick_data
from backend.indicators.adx import calculate_adx_slope

logger = logging.getLogger(__name__)

REVERSAL_RSI_DIFF = float(os.getenv("REVERSAL_RSI_DIFF", "15"))

# ────────────────────────────────────────────────
#  EMA helper for exit‑filter
# ────────────────────────────────────────────────
def _ema_flat_or_cross(
    fast: pd.Series,
    slow: pd.Series,
    side: str,
    pip_size: float = 0.01
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
        series.iloc[-(lookback + 1):-1] if hasattr(series, "iloc") else series[-(lookback + 1):-1]
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
) -> bool:
    """
    Pure rule‑based entry filter.
    Returns True when market conditions warrant querying the AI entry decision.

    Parameters
    ----------
    indicators : dict
        Indicator dictionary returned by ``calculate_indicators``.
    price : float | None
        Latest market price used for Bollinger band deviation checks.
    indicators_m1 : dict | None
        Optional M1 timeframe indicator dictionary. If not provided, the
        function attempts to fetch M1 candles and compute indicators.
    indicators_m15 : dict | None
        Optional M15 timeframe indicator dictionary used for rapid reversal
        checks. If omitted, the function fetches M15 candles as needed.
    """
    if os.getenv("DISABLE_ENTRY_FILTER", "false").lower() == "true":
        return True

    # --- Time‑of‑day block (JST decimal hours) --------------------------
    quiet_start = float(os.getenv("QUIET_START_HOUR_JST", "3"))   # default 03:00
    quiet_end   = float(os.getenv("QUIET_END_HOUR_JST", "7"))     # default 07:00

    now_jst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    current_time = now_jst.hour + now_jst.minute / 60.0

    in_quiet_hours = (
        (quiet_start < quiet_end  and quiet_start <= current_time < quiet_end) or
        (quiet_start > quiet_end  and (current_time >= quiet_start or current_time < quiet_end)) or
        (quiet_start == quiet_end)
    )
    if in_quiet_hours:
        logger.debug(f"EntryFilter blocked by quiet hours ({quiet_start}-{quiet_end})")
        return False

    # --- Pivot suppression for specified timeframes --------------------
    if os.getenv("HIGHER_TF_ENABLED", "true").lower() == "true":
        pair = os.getenv("DEFAULT_PAIR", "USD_JPY")
        tfs = [
            tf.strip().upper()
            for tf in os.getenv("PIVOT_SUPPRESSION_TFS", "D").split(",")
            if tf.strip()
        ]
        higher = analyze_higher_tf(pair)
        tick = fetch_tick_data(pair)
        current_price = float(tick["prices"][0]["bids"][0]["price"])
        pip_size = float(os.getenv("PIP_SIZE", "0.01"))
        sup_pips = float(os.getenv("PIVOT_SUPPRESSION_PIPS", "15"))
        for tf in tfs:
            pivot = higher.get(f"pivot_{tf.lower()}")
            if pivot is None:
                continue
            if abs((current_price - pivot) / pip_size) <= sup_pips:
                logger.debug(
                    f"EntryFilter blocked: within {sup_pips} pips of {tf} pivot"
                )
                return False

    # --- Range / Volatility metrics ------------------------------------
    rsi_series = indicators["rsi"]
    atr_series = indicators["atr"]
    adx_series = indicators.get("adx")
    latest_adx = adx_series.iloc[-1] if adx_series is not None and len(adx_series) else None

    adx_thresh = float(os.getenv("ADX_RANGE_THRESHOLD", "25"))
    range_mode = latest_adx is not None and latest_adx < adx_thresh
    lookback = int(os.getenv("ADX_SLOPE_LOOKBACK", "3"))
    adx_slope = calculate_adx_slope(adx_series, lookback) if adx_series is not None else 0.0
    if adx_slope < 0:
        range_mode = True

    # --- Volume check ---------------------------------------------------
    vol_series = indicators.get("volume")
    vol_ok = True
    ma_period = int(os.getenv("VOL_MA_PERIOD", "5"))
    if vol_series is not None and len(vol_series) >= ma_period:
        sma_vol = vol_series.rolling(window=ma_period).mean().iloc[-1]
        min_vol = float(os.getenv("MIN_VOL_MA", os.getenv("MIN_VOL_M1", "60")))
        vol_ok = sma_vol >= min_vol
        if not vol_ok:
            logger.debug("EntryFilter blocked: volume below threshold")
            return False

    # --- M1 RSI cross-up/down check ----------------------------------
    strict = os.getenv("STRICT_ENTRY_FILTER", "true").lower() == "true"
    if strict:
        if indicators_m1 is None:
            try:
                from backend.market_data.candle_fetcher import fetch_candles
                from backend.indicators.calculate_indicators import calculate_indicators

                pair = os.getenv("DEFAULT_PAIR", "USD_JPY")
                candles_m1 = fetch_candles(
                    pair,
                    granularity="M1",
                    count=10,
                    allow_incomplete=True,
                )
                indicators_m1 = calculate_indicators(candles_m1, pair=pair)
            except Exception as exc:
                logger.warning("Failed to fetch M1 indicators: %s", exc)
                indicators_m1 = None

        if indicators_m1 and indicators_m1.get("rsi") is not None:
            lookback = int(os.getenv("RSI_CROSS_LOOKBACK", "1"))
            if not _rsi_cross_up_or_down(indicators_m1["rsi"], lookback=lookback):
                logger.debug(
                    "EntryFilter blocked: M1 RSI did not show cross up/down signal"
                )
                return False

    # --- Rapid reversal block ---------------------------------------
    if indicators_m15 is None:
        try:
            from backend.market_data.candle_fetcher import fetch_candles
            from backend.indicators.calculate_indicators import calculate_indicators

            pair = os.getenv("DEFAULT_PAIR", "USD_JPY")
            candles_m15 = fetch_candles(
                pair,
                granularity="M15",
                count=20,
                allow_incomplete=True,
            )
            indicators_m15 = calculate_indicators(candles_m15, pair=pair)
        except Exception as exc:
            logger.warning("Failed to fetch M15 indicators: %s", exc)
            indicators_m15 = None

    if (
        indicators_m15
        and indicators_m15.get("rsi") is not None
        and indicators.get("macd_hist") is not None
        and rapid_reversal_block(indicators["rsi"], indicators_m15["rsi"], indicators["macd_hist"])
    ):
        logger.debug("EntryFilter blocked: rapid reversal detected")
        return False

    ema_fast = indicators["ema_fast"]
    ema_slow = indicators["ema_slow"]

    latest_rsi = rsi_series.iloc[-1] if len(rsi_series) else None
    latest_atr = atr_series.iloc[-1] if len(atr_series) else None
    latest_ema_fast = ema_fast.iloc[-1] if len(ema_fast) else None
    latest_ema_slow = ema_slow.iloc[-1] if len(ema_slow) else None
    prev_ema_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else None
    prev_ema_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else None
    ema_flat_thresh = float(os.getenv("EMA_FLAT_PIPS", "0.05")) * float(os.getenv("PIP_SIZE", "0.01"))

    if len(ema_fast) >= 3 and len(ema_slow) >= 2:
        prev_slope = prev_ema_fast - ema_fast.iloc[-3]
        curr_slope = latest_ema_fast - prev_ema_fast
        diff_prev = prev_ema_fast - prev_ema_slow
        diff_curr = latest_ema_fast - latest_ema_slow
        narrowing = abs(diff_curr) < abs(diff_prev)
        rev_or_flat = (curr_slope * prev_slope < 0) or abs(curr_slope) <= ema_flat_thresh
        if narrowing and rev_or_flat:
            logger.debug("EntryFilter blocked: EMA convergence with slope reversal/flat")
            return False

    # --- Bollinger Band width check ------------------------------------
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    bb_middle = indicators.get("bb_middle")
    band_width_ok = False
    bw_pips = None
    bw_thresh = float(os.getenv("BAND_WIDTH_THRESH_PIPS", "4"))
    if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
        pip_size = float(os.getenv("PIP_SIZE", "0.01"))
        bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
        band_width_ok = bw_pips >= bw_thresh
        if bw_pips <= bw_thresh:
            # バンド幅が閾値以下ならレンジモード扱い
            range_mode = True

        # Overshoot check --------------------------------------------------
        overshoot_mult = float(os.getenv("OVERSHOOT_ATR_MULT", "1.0"))
        threshold = bb_lower.iloc[-1] - atr_series.iloc[-1] * overshoot_mult
        if price is not None and price <= threshold:
            logger.debug("EntryFilter blocked: price overshoot below lower BB")
            return False

    # --- Dynamic ADX threshold based on BB width -----------------------
    adx_base = float(os.getenv("ADX_RANGE_THRESHOLD", "25"))
    coeff = float(os.getenv("ADX_DYNAMIC_COEFF", "0"))
    width_ratio = ((bw_pips - bw_thresh) / bw_thresh) if bw_pips is not None else 0.0
    adx_thresh = adx_base * (1 + coeff * width_ratio)
    range_mode = latest_adx is not None and latest_adx < adx_thresh

    # DI cross overrides trend judgement
    plus_di = indicators.get("plus_di")
    minus_di = indicators.get("minus_di")
    di_cross = False
    if plus_di is not None and minus_di is not None and len(plus_di) >= 2:
        try:
            p_prev = float(plus_di.iloc[-2]) if hasattr(plus_di, "iloc") else float(plus_di[-2])
            p_cur = float(plus_di.iloc[-1]) if hasattr(plus_di, "iloc") else float(plus_di[-1])
            m_prev = float(minus_di.iloc[-2]) if hasattr(minus_di, "iloc") else float(minus_di[-2])
            m_cur = float(minus_di.iloc[-1]) if hasattr(minus_di, "iloc") else float(minus_di[-1])
            di_cross = (p_prev > m_prev and p_cur < m_cur) or (p_prev < m_prev and p_cur > m_cur)
        except Exception:
            di_cross = False
    if di_cross:
        range_mode = True

    # --- Range center block --------------------------------------------
    block_pct = float(os.getenv("RANGE_CENTER_BLOCK_PCT", "0.3"))
    if (
        range_mode
        and price is not None
        and bb_upper is not None
        and bb_lower is not None
        and bb_middle is not None
        and len(bb_upper)
        and len(bb_lower)
        and len(bb_middle)
    ):
        band_span = bb_upper.iloc[-1] - bb_lower.iloc[-1]
        if band_span != 0:
            deviation = abs(price - bb_middle.iloc[-1]) / band_span
            if deviation < block_pct:
                logger.debug(
                    "EntryFilter blocked: price near BB center in range mode"
                )
                return False

    def _is_nan(v):
        try:
            return v != v
        except Exception:
            return False

    if _is_nan(latest_atr) or _is_nan(latest_adx):
        logger.debug(
            "EntryFilter bypassed: ATR/ADX history insufficient"
        )
        return True

    if None in [latest_rsi, latest_ema_fast, latest_ema_slow, prev_ema_fast, prev_ema_slow]:
        logger.debug("EntryFilter blocked: insufficient indicator history")
        return False  # insufficient data

    # --- Composite conditions ------------------------------------------
    lower = float(os.getenv("RSI_ENTRY_LOWER", "20"))
    upper = float(os.getenv("RSI_ENTRY_UPPER", "80"))

    pip_size = float(os.getenv("PIP_SIZE", "0.01"))
    atr_th = float(os.getenv("ATR_ENTRY_THRESHOLD", "0.09"))

    if range_mode:
        atr_condition = True  # ignore ATR in range market
    else:
        atr_condition = (latest_atr / pip_size) >= (atr_th / pip_size)

    rsi_condition = latest_rsi < lower or latest_rsi > upper

    ema_cross_up = prev_ema_fast < prev_ema_slow and latest_ema_fast > latest_ema_slow
    ema_cross_down = prev_ema_fast > prev_ema_slow and latest_ema_fast < latest_ema_slow
    ema_condition = ema_cross_up or ema_cross_down

    score = sum([rsi_condition, atr_condition, ema_condition])
    required = 1  # adjust if you want stricter logic

    if not band_width_ok:
        logger.debug(
            f"EntryFilter blocked: Bollinger band width {bw_pips:.2f} pips < {bw_thresh}"
        )
        return False

    if score < required:
        if not atr_condition:
            logger.debug(
                f"EntryFilter blocked: ATR {latest_atr:.4f} below {atr_th}"
            )
        if not rsi_condition:
            logger.debug(
                f"EntryFilter blocked: RSI {latest_rsi:.2f} between {lower} and {upper}"
            )
        if not ema_condition:
            logger.debug("EntryFilter blocked: EMA cross condition not met")
        return False

    return True


# ────────────────────────────────────────────────
#  エグジット用フィルター（必要なら後で拡張）
# ────────────────────────────────────────────────
def pass_exit_filter(indicators: dict, position_side: str) -> bool:
    # --- Test override: set DISABLE_EXIT_FILTER=true in .env to bypass all exit filters
    if os.getenv("DISABLE_EXIT_FILTER", "false").lower() == "true":
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

    lower = float(os.getenv("RSI_EXIT_LOWER", "35"))
    upper = float(os.getenv("RSI_EXIT_UPPER", "65"))
    atr_th = float(os.getenv("ATR_EXIT_THRESHOLD", "0.04"))

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
    pip_size = float(os.getenv("PIP_SIZE", "0.01"))
    flat_or_cross = _ema_flat_or_cross(ema_fast, ema_slow, position_side, pip_size)

    return (in_neutral_band and atr_is_calm) or cross_signal or flat_or_cross
