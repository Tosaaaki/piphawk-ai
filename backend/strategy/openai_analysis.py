import logging
import json
from backend.utils.openai_client import ask_openai
from backend.utils import env_loader, parse_json_answer
from backend.strategy.pattern_ai_detection import detect_chart_pattern
from backend.strategy.pattern_scanner import PATTERN_DIRECTION
from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
import pandas as pd

# --- Added for AI-based exit decision ---
# Consolidated exit decision helpers live in exit_ai_decision
from backend.strategy.exit_ai_decision import AIDecision, evaluate as evaluate_exit
import time
from datetime import datetime

# ----------------------------------------------------------------------
# Config – driven by environment variables
# ----------------------------------------------------------------------
AI_COOLDOWN_SEC_FLAT: int = int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", 60))
AI_COOLDOWN_SEC_OPEN: int = int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", 30))
# Regime‑classification specific cooldown (defaults to flat cooldown)
AI_REGIME_COOLDOWN_SEC: int = int(env_loader.get_env("AI_REGIME_COOLDOWN_SEC", AI_COOLDOWN_SEC_FLAT))

# --- Threshold for AI‑proposed TP probability ---
MIN_TP_PROB: float = float(env_loader.get_env("MIN_TP_PROB", "0.75"))
TP_PROB_HOURS: int = int(env_loader.get_env("TP_PROB_HOURS", "24"))
LIMIT_THRESHOLD_ATR_RATIO: float = float(env_loader.get_env("LIMIT_THRESHOLD_ATR_RATIO", "0.3"))
MAX_LIMIT_AGE_SEC: int = int(env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))
MIN_NET_TP_PIPS: float = float(env_loader.get_env("MIN_NET_TP_PIPS", "2"))
BE_TRIGGER_PIPS: int = int(env_loader.get_env("BE_TRIGGER_PIPS", 10))
AI_LIMIT_CONVERT_MODEL: str = env_loader.get_env("AI_LIMIT_CONVERT_MODEL", "gpt-4.1-nano")
# --- Exit bias factor ---
EXIT_BIAS_FACTOR: float = float(env_loader.get_env("EXIT_BIAS_FACTOR", "1.0"))

# --- Volatility and ADX filters ---
COOL_BBWIDTH_PCT: float = float(env_loader.get_env("COOL_BBWIDTH_PCT", "0"))
COOL_ATR_PCT: float = float(env_loader.get_env("COOL_ATR_PCT", "0"))
ADX_NO_TRADE_MIN: float = float(env_loader.get_env("ADX_NO_TRADE_MIN", "20"))
ADX_NO_TRADE_MAX: float = float(env_loader.get_env("ADX_NO_TRADE_MAX", "30"))
USE_LOCAL_PATTERN: bool = (
    env_loader.get_env("USE_LOCAL_PATTERN", "false").lower() == "true"
)
# Local/AI blending threshold for market regime decision
LOCAL_WEIGHT_THRESHOLD: float = float(
    env_loader.get_env("LOCAL_WEIGHT_THRESHOLD", "0.6")
)

# Global variables to store last AI call timestamps
_last_entry_ai_call_time = 0.0
_last_exit_ai_call_time = 0.0
# Regime‑AI cache
_last_regime_ai_call_time = 0.0

_cached_regime_result: dict | None = None


def _series_tail_list(series, n: int = 20) -> list:
    """Return the last ``n`` values from a pandas Series or list."""
    if series is None:
        return []
    try:
        if hasattr(series, "iloc"):
            return series.iloc[-n:].tolist()
        if isinstance(series, (list, tuple)):
            return list(series)[-n:]
        return [series]
    except Exception:
        return []

def get_ai_cooldown_sec(current_position: dict | None) -> int:
    """
    現在ポジションがある場合は ``AI_COOLDOWN_SEC_FLAT``、
    ポジションが無い場合は ``AI_COOLDOWN_SEC_OPEN`` を返す。
    """
    if current_position:
        try:
            units_val = float(current_position.get("units", 0))
        except (TypeError, ValueError):
            units_val = 0.0
        if units_val == 0:
            try:
                units_val = float(current_position.get("long", {}).get("units", 0))
            except (TypeError, ValueError):
                units_val = 0.0
            if units_val == 0:
                try:
                    units_val = float(current_position.get("short", {}).get("units", 0))
                except (TypeError, ValueError):
                    units_val = 0.0
        if abs(units_val) > 0:
            return AI_COOLDOWN_SEC_FLAT
    return AI_COOLDOWN_SEC_FLAT

logger = logging.getLogger(__name__)

logger.info("OpenAI Analysis started")


# ----------------------------------------------------------------------
# Consistency scoring
# ----------------------------------------------------------------------
def calc_consistency(
    local: str | None,
    ai: str | None,
    ema_ok: float = 0.0,
    adx_ok: float = 0.0,
    rsi_cross_ok: float = 0.0,
) -> float:
    """Return a blended consistency score between local indicators and AI."""

    if not local or not ai:
        ai_score = 0.5
    else:
        ai_score = 1.0 if local == ai else 0.0

    local_score = ema_ok * 0.4 + adx_ok * 0.3 + rsi_cross_ok * 0.3

    alpha = LOCAL_WEIGHT_THRESHOLD * local_score + (1 - LOCAL_WEIGHT_THRESHOLD) * ai_score
    return alpha



# ----------------------------------------------------------------------
# Market‑regime classification helper (OpenAI direct, enhanced English prompt)
# ----------------------------------------------------------------------
from backend.strategy.range_break import detect_range_break, classify_breakout


def get_market_condition(context: dict, higher_tf: dict | None = None) -> dict:
    """
    Determine whether the market is in a 'trend' or 'range' state.
        The function combines a heuristic, indicator‑based assessment
    (ADX + EMA slope) with an LLM assessment.  
    If both disagree, the local heuristic wins.

    Returns
    -------
    dict
        {
            "market_condition": "trend" | "range",
            "range_break": "up" | "down" | None,
            "break_class": "trend" | "range" | None,
        }
    ``context`` may include ``indicators_h1`` and ``indicators_h4`` to
    improve the local regime decision.
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    indicators = context.get("indicators", {})

    # ------------------------------------------------------------------
    # 1) Local regime assessment (ADX + EMA slope consistency)
    # ------------------------------------------------------------------
    adx_vals = indicators.get("adx")
    ema_vals = indicators.get("ema_slope")
    ind_m1 = context.get("indicators_m1") or {}
    ind_h1 = context.get("indicators_h1") or {}
    ind_h4 = context.get("indicators_h4") or {}

    def _extract_latest(series):
        if series is None:
            return []
        try:
            if hasattr(series, "iloc"):
                return [float(x) for x in series.iloc[-3:]]
            if isinstance(series, (list, tuple)):
                return [float(x) for x in series[-3:]]
            return [float(series)]
        except Exception:
            return []

    # latest ADX value
    adx_latest = None
    if adx_vals is not None:
        try:
            if hasattr(adx_vals, "iloc"):
                adx_latest = float(adx_vals.iloc[-1])
            elif isinstance(adx_vals, (list, tuple)):
                adx_latest = float(adx_vals[-1]) if adx_vals else None
            else:
                adx_latest = float(adx_vals)
        except Exception:
            adx_latest = None

    # EMAの傾きが無い場合はema_fastから代用の傾きを算出
    ema_series = _extract_latest(ema_vals)
    if not ema_series:
        fast_vals = indicators.get("ema_fast")
        fast_series = _extract_latest(fast_vals)
        if len(fast_series) >= 2:
            ema_series = [fast_series[i] - fast_series[i - 1] for i in range(1, len(fast_series))]
    ema_sign_consistent = False
    if len(ema_series) >= 2:
        pos = [v > 0 for v in ema_series]
        neg = [v < 0 for v in ema_series]
        ema_sign_consistent = all(pos) or all(neg)
    ema_ok = 1.0 if ema_sign_consistent else 0.0

    adx_ok = 1.0 if adx_latest is not None and adx_latest >= 20 else 0.0

    rsi_cross_ok = 0.0
    rsi_m1 = ind_m1.get("rsi")
    if rsi_m1 is not None:
        try:
            from backend.strategy.signal_filter import _rsi_cross_up_or_down
            if _rsi_cross_up_or_down(rsi_m1):
                rsi_cross_ok = 1.0
        except Exception:
            rsi_cross_ok = 0.0

    # Bollinger Band width check (narrow band implies range)
    narrow_bw = False
    bw_pips = None
    try:
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
            bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
            narrow_bw = bw_pips <= bw_thresh
    except Exception:
        narrow_bw = False

    local_regime = None
    if adx_latest is not None and ema_sign_consistent:
        local_regime = "trend" if adx_latest >= 20 else "range"

    def _is_trend(ind: dict) -> bool | None:
        adx = ind.get("adx")
        ema = ind.get("ema_slope")
        if adx is None or ema is None:
            return None
        try:
            if hasattr(adx, "iloc"):
                adx_val = float(adx.iloc[-1])
            elif isinstance(adx, (list, tuple)):
                adx_val = float(adx[-1]) if adx else None
            else:
                adx_val = float(adx)
        except Exception:
            adx_val = None
        ema_series = _extract_latest(ema)
        ema_ok_local = len(ema_series) >= 3 and (
            all(v > 0 for v in ema_series) or all(v < 0 for v in ema_series)
        )
        if adx_val is None or not ema_ok_local:
            return None
        return adx_val >= 20

    if local_regime != "trend":
        for ind in (ind_h4, ind_h1):
            if _is_trend(ind):
                local_regime = "trend"
                break

    if narrow_bw:
        local_regime = "range"

    # ------------------------------------------------------------------
    # 2) LLM assessment (JSON‑only response)
    # ------------------------------------------------------------------
    prompt = (
        "Based on the current market data and indicators provided below, "
        "determine whether the market is in a 'trend' or 'range' state.\n\n"
        "### Evaluation Criteria:\n"
        "- Short‑term price action: consecutive candles strongly moving in one "
        "  direction suggest a trend.\n"
        "- EMA slope and price relationship: prices consistently above or below "
        "  EMA indicate a trending market.\n"
        "- ADX value: a value above 25 typically indicates a trending market.\n"
        "- RSI extremes: extremely low or high RSI values can suggest range‑bound "
        "  conditions but must be evaluated alongside short‑term price movements.\n\n"
        "If RSI stays consistently near or below 30 for multiple candles, this "
        "indicates a strong bearish trend rather than oversold range conditions.\n"
        "Conversely, if RSI stays consistently near or above 70 for multiple "
        "candles, this indicates a strong bullish trend rather than overbought "
        "range conditions.\n"
        + (
            f"Bollinger band width has contracted to {bw_pips:.1f} pips; range may be forming.\n"
            if narrow_bw and bw_pips is not None
            else ""
        )
        + f"### Market Data and Indicators:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        "Respond with JSON: {\"market_condition\":\"trend|range\"}"
    )

    try:
        # Request JSON‑object response if the client supports it
        llm_raw = ask_openai(
            prompt,
            response_format={"type": "json_object"},
        )
        if isinstance(llm_raw, dict):        # already parsed
            llm_regime = llm_raw.get("market_condition", "range")
        else:
            llm_regime = json.loads(llm_raw).get("market_condition", "range")
    except Exception as exc:
        logger.error("get_market_condition ‑ LLM failure: %s", exc)
        llm_regime = "range"

    # ------------------------------------------------------------------
    # 3) Reconcile local vs LLM assessments using consistency score
    # ------------------------------------------------------------------
    alpha = calc_consistency(
        local_regime, llm_regime, ema_ok=ema_ok, adx_ok=adx_ok, rsi_cross_ok=rsi_cross_ok
    )
    local_score = 1.0 if local_regime == "trend" else 0.0
    ai_score = 1.0 if llm_regime == "trend" else 0.0
    blended = alpha * local_score + (1 - alpha) * ai_score
    final_regime = "trend" if blended >= 0.5 else "range"

    if local_regime and llm_regime != local_regime:
        if alpha >= LOCAL_WEIGHT_THRESHOLD:
            final_regime = local_regime
        elif (1 - alpha) >= LOCAL_WEIGHT_THRESHOLD:
            final_regime = llm_regime

    if local_regime and llm_regime != local_regime:
        logger.warning(
            "LLM regime '%s' conflicts with local regime '%s'; alpha=%.2f -> %s",
            llm_regime,
            local_regime,
            alpha,
            final_regime,
        )

    # ------------------------------------------------------------------
    # 4) Optional range‑break analysis
    # ------------------------------------------------------------------
    range_break = None
    break_class = None
    candles = context.get("candles_m5")
    if candles:
        pivot = None
        if higher_tf:
            pivot = higher_tf.get("pivot_h1") or higher_tf.get("pivot_h4") or higher_tf.get("pivot_d")
        br = detect_range_break(candles, pivot=pivot)
        if br["break"]:
            range_break = br["direction"]
            break_class = classify_breakout(indicators)
            if break_class == "trend":
                final_regime = "trend"

    return {
        "market_condition": final_regime,
        "range_break": range_break,
        "break_class": break_class,
    }



# ----------------------------------------------------------------------
# Entry decision
# ----------------------------------------------------------------------
def get_entry_decision(market_data, strategy_params, indicators=None, candles_dict=None, market_cond=None, higher_tf=None):
    plan = get_trade_plan(market_data, indicators or {}, candles_dict or {}, strategy_params)
    return plan.get("entry", {"side": "no"})



# ----------------------------------------------------------------------
# Exit decision
# ----------------------------------------------------------------------
def get_exit_decision(
    market_data,
    current_position,
    indicators=None,
    entry_regime=None,
    market_cond=None,
    higher_tf=None,
    indicators_m1: dict | None = None,
    candles: list | None = None,
    patterns: list[str] | None = None,
    detected_patterns: dict[str, str | None] | None = None,
):
    """
    Ask the LLM whether we should exit an existing position.
    Returns a JSON-formatted string like:
        {"action":"EXIT","reason":"Price above BB upper"}

    higher_tf (dict|None): higher‑timeframe reference levels
    """
    global _last_exit_ai_call_time
    now = time.time()
    cooldown = get_ai_cooldown_sec(current_position)
    if now - _last_exit_ai_call_time < cooldown:
        logger.info("Exit decision skipped (cooldown)")
        return {"action": "HOLD", "reason": "Cooldown active"}

    if indicators is None:
        indicators = {}

    # Ensure ADX is present for regime‑shift reasoning
    if "adx" not in indicators and "adx" in market_data:
        indicators["adx"] = market_data.get("adx")

    higher_tf_json = json.dumps(higher_tf) if higher_tf else "{}"
    market_cond_json = json.dumps(market_cond) if market_cond else "{}"
    entry_regime_json = json.dumps(entry_regime) if entry_regime else "{}"

    units_val = float(current_position.get("units", 0))
    side = "SHORT" if units_val < 0 else "LONG"

    # --- 現在値とエントリ価格からサイド別の差分を算出する ---
    try:
        bid = float(market_data.get("bid")) if isinstance(market_data, dict) else None
        ask = float(market_data.get("ask")) if isinstance(market_data, dict) else None
        avg_price = float(current_position.get("average_price"))
        if side == "LONG" and bid is not None:
            pips_from_entry = (bid - avg_price) * 100
            unreal_pnl = (bid - avg_price) * units_val
        elif side == "SHORT" and ask is not None:
            pips_from_entry = (avg_price - ask) * 100
            unreal_pnl = (avg_price - ask) * -units_val
        else:
            pips_from_entry = 0
            unreal_pnl = 0
    except (ValueError, TypeError):
        pips_from_entry = 0
        unreal_pnl = 0

    secs_since_entry = market_data.get("secs_since_entry")

    if secs_since_entry is None:
        try:
            entry_time_str = current_position.get("entry_time") or current_position.get("openTime")
            if entry_time_str:
                entry_dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                secs_since_entry = (datetime.utcnow() - entry_dt).total_seconds()
        except Exception:
            secs_since_entry = None

    # --------------------------------------------------------------
    # Break‑even trigger (fallback)
    # --------------------------------------------------------------
    if pips_from_entry is None:
        try:
            bid = float(market_data.get("bid")) if isinstance(market_data, dict) else None
            ask = float(market_data.get("ask")) if isinstance(market_data, dict) else None
            avg_price = float(current_position.get("average_price"))
            if side == "LONG" and bid:
                pips_from_entry = (bid - avg_price) * 100
            elif side == "SHORT" and ask:
                pips_from_entry = (avg_price - ask) * 100
            else:
                pips_from_entry = 0
        except (ValueError, TypeError):
            pips_from_entry = 0

    breakeven_reached = pips_from_entry >= BE_TRIGGER_PIPS

    # Ensure all indicator values are JSON serializable (e.g., pandas Series to list)
    indicators_serializable = {
        key: value.tolist() if hasattr(value, "tolist") else value
        for key, value in indicators.items()
    }
    indicators_m1_serializable = (
        {
            key: value.tolist() if hasattr(value, "tolist") else value
            for key, value in indicators_m1.items()
        }
        if indicators_m1
        else {}
    )

    pattern_name = None
    if patterns:
        try:
            if USE_LOCAL_PATTERN:
                from backend.strategy.pattern_scanner import scan_all
                pattern_name = scan_all(candles or [])
            else:
                pattern_res = detect_chart_pattern(candles or [], patterns)
                pattern_name = pattern_res.get("pattern")
        except Exception:
            pattern_name = None

    pattern_line = None
    if detected_patterns:
        try:
            pattern_line = ", ".join(
                f"{tf}:{p}" for tf, p in detected_patterns.items() if p
            ) or None
        except Exception:
            pattern_line = str(detected_patterns)
    elif pattern_name:
        pattern_line = pattern_name
            
    prompt = (
        "You are an expert FX trader AI. Your job is to decide, with clear and concise reasoning, whether to HOLD or EXIT an open position based on the latest market context and indicators.\n"
        f"EXIT_BIAS_FACTOR={EXIT_BIAS_FACTOR} (>1 favors EXIT, <1 favors HOLD).\n\n"
        f"### Position Details\n"
        f"- Side: {side}\n"
        f"- Time Since Entry: {secs_since_entry if secs_since_entry is not None else 'N/A'} sec\n"
        f"- Pips From Entry: {pips_from_entry:.1f}\n"
        f"- Unrealized P&L: {unreal_pnl}\n"
        f"- Entry Regime: {entry_regime_json}\n"
        f"- Market Condition: {market_cond_json}\n"
        f"- Higher Timeframe Levels: {higher_tf_json}\n"
        f"- Chart Pattern: {pattern_line if pattern_line else 'None'}\n"
        "\n"
        "### Market Data & Indicators\n"
        f"{json.dumps(market_data, ensure_ascii=False)}\n"
        f"{json.dumps(indicators_serializable, ensure_ascii=False)}\n"
        f"{json.dumps(indicators_m1_serializable, ensure_ascii=False)}\n"
        "\n"
        "### Decision Framework\n"
        "1. **Classify the market state as 'trend' or 'range'** using ADX, EMA, RSI, and Bollinger Bands:\n"
        "   - *Trend*: ADX > 25, clear EMA slope, price persistently above/below EMA or BB midline.\n"
        "   - *Range*: ADX < 25, flat EMA, price oscillates around EMA or BB midline.\n"
        "2. **LONG position:**\n"
        "   - HOLD if trend indicators (up EMA slope, ADX > 25, price upper BB) show ongoing strength.\n"
        "   - EXIT if RSI > 70 with price stalling at upper BB, or momentum weakens.\n"
        "3. **SHORT position:**\n"
        "   - HOLD if trend indicators (down EMA slope, ADX > 25, price lower BB) show ongoing strength.\n"
        "   - EXIT if RSI < 30 with price stalling at lower BB, or momentum weakens.\n"
        "4. **Post-entry stability:**\n"
        "   - Avoid exits within 5 minutes or ±5 pips of entry unless a clear reversal or major warning appears.\n"
        "5. **General:**\n"
        "   - Ignore minor fluctuations; do not exit on a single chart pattern or RSI alone.\n"
        "   - Consider EXIT only when at least two reversal signals align (e.g., pattern + EMA reversal, pattern + ADX drop).\n"
        "\n"
        "### Response Instructions\n"
        "- Output valid one-line JSON: {\"action\":\"EXIT\"|\"HOLD\",\"reason\":\"Concise reason, max 25 words\"}\n"
        "- Do not output anything except the JSON object.\n"
        "- Example: {\"action\":\"HOLD\",\"reason\":\"Upward EMA and strong ADX; trend likely to continue.\"}\n"
        "- Example: {\"action\":\"EXIT\",\"reason\":\"RSI overbought and price stalling at upper Bollinger Band.\"}\n"
    )
    response_json = ask_openai(prompt)
    _last_exit_ai_call_time = now
    logger.debug(f"[get_exit_decision] prompt sent:\n{prompt}")
    logger.info(f"OpenAI response: {response_json}")

    # --- Pattern direction consistency check -----------------------------
    try:
        action = str(response_json.get("action", "")).upper()
        reason_text = str(response_json.get("reason", "")).lower()
        if action == "EXIT":
            for pat, direction in PATTERN_DIRECTION.items():
                if pat in reason_text:
                    pos_dir = "bullish" if side == "LONG" else "bearish"
                    logger.info(
                        "exit_reason pattern=%s dir=%s pos_side=%s",
                        pat,
                        direction,
                        side,
                    )
                    if direction == pos_dir:
                        logger.warning(
                            "AI EXIT contradicted by pattern orientation; overriding to HOLD"
                        )
                        response_json["action"] = "HOLD"
                    break
    except Exception as exc:
        logger.error(f"pattern check failed: {exc}")

    # --- Trend consistency check -------------------------------------------
    try:
        if response_json.get("action", "").upper() == "EXIT":
            adx_series = indicators.get("adx")
            ema_fast_series = indicators.get("ema_fast")
            ema_slow_series = indicators.get("ema_slow")
            if adx_series is not None and ema_fast_series is not None:
                last_adx = (
                    float(adx_series.iloc[-1]) if hasattr(adx_series, "iloc") else float(adx_series[-1])
                )
                if last_adx >= 25:
                    # Determine EMA slope over last 3 candles
                    if hasattr(ema_fast_series, "iloc") and len(ema_fast_series) >= 3:
                        ema_last = float(ema_fast_series.iloc[-1])
                        ema_prev = float(ema_fast_series.iloc[-3])
                    elif isinstance(ema_fast_series, (list, tuple)) and len(ema_fast_series) >= 3:
                        ema_last = float(ema_fast_series[-1])
                        ema_prev = float(ema_fast_series[-3])
                    else:
                        ema_last = None
                        ema_prev = None
                    if ema_last is not None and ema_prev is not None:
                        slope = ema_last - ema_prev
                        trend_cont = False
                        if side == "LONG" and slope > 0:
                            trend_cont = True
                        elif side == "SHORT" and slope < 0:
                            trend_cont = True
                        if trend_cont:
                            logger.warning(
                                "AI EXIT overridden: strong trend indicators in favor of current position"
                            )
                            response_json["action"] = "HOLD"
    except Exception as exc:
        logger.error(f"trend consistency check failed: {exc}")

    return response_json



# ----------------------------------------------------------------------
# TP / SL adjustment helper
# ----------------------------------------------------------------------
def get_tp_sl_adjustment(market_data, current_tp, current_sl):
    # TP/SL is now decided in get_trade_plan; no further adjustment needed.
    return "No adjustment"


# ----------------------------------------------------------------------
# Unified LLM call: regime → entry → TP/SL & probabilities
# ----------------------------------------------------------------------
def get_trade_plan(
    market_data: dict,
    indicators: dict[str, dict],
    candles_dict: dict[str, list],
    hist_stats: dict | None = None,
    patterns: list[str] | None = None,
    pattern_tf: str = "M5",
    detected_patterns: dict[str, str | None] | None = None,
) -> dict:
    """
    Single‑shot call to the LLM that returns a dict:
        {
          "regime": {...},
          "entry":  {...},
          "risk":   {...}
        }
    ``indicators`` should map timeframe labels (e.g. "M5", "M1") to their
    respective indicator dictionaries. ``candles_dict`` likewise contains a
    list of candles for each timeframe.

    The function also performs local guards:
        • tp_prob ≥ MIN_TP_PROB
        • expected value (tp*tp_prob – sl*sl_prob) > 0
      If either guard fails, it forces ``side:"no"``.
    """
    ind_m5 = indicators.get("M5", {})
    ind_m1 = indicators.get("M1", {})
    ind_d1 = indicators.get("D1", indicators.get("D", {}))
    candles_m5 = candles_dict.get("M5", [])
    candles_m1 = candles_dict.get("M1", [])
    candles_d1 = candles_dict.get("D1", candles_dict.get("D", []))

    pattern_name = None
    if patterns:
        try:
            tf_candles = candles_dict.get(pattern_tf, [])
            if USE_LOCAL_PATTERN:
                from backend.strategy.pattern_scanner import scan_all
                pattern_name = scan_all(tf_candles)
            else:
                pattern_res = detect_chart_pattern(tf_candles, patterns)
                pattern_name = pattern_res.get("pattern")
        except Exception:
            pattern_name = None

    pattern_line = None
    if detected_patterns:
        try:
            pattern_line = ", ".join(
                f"{tf}:{p}" for tf, p in detected_patterns.items() if p
            ) or None
        except Exception:
            pattern_line = str(detected_patterns)
    elif pattern_name:
        pattern_line = pattern_name

    # --------------------------------------------------------------
    # Estimate market "noise" from ATR and Bollinger band width
    # --------------------------------------------------------------
    noise_pips = None
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        atr_series = ind_m5.get("atr")
        bb_upper = ind_m5.get("bb_upper")
        bb_lower = ind_m5.get("bb_lower")

        atr_val = None
        if atr_series is not None:
            if hasattr(atr_series, "iloc"):
                atr_val = float(atr_series.iloc[-1])
            else:
                atr_val = float(atr_series[-1])
        bw_val = None
        if bb_upper is not None and bb_lower is not None:
            if hasattr(bb_upper, "iloc"):
                bb_u = float(bb_upper.iloc[-1])
            else:
                bb_u = float(bb_upper[-1])
            if hasattr(bb_lower, "iloc"):
                bb_l = float(bb_lower.iloc[-1])
            else:
                bb_l = float(bb_lower[-1])
            bw_val = bb_u - bb_l

        atr_pips = atr_val / pip_size if atr_val is not None else 0.0
        bw_pips = bw_val / pip_size if bw_val is not None else 0.0
        noise_pips = max(atr_pips, bw_pips)
    except Exception:
        noise_pips = None

    noise_val = f"{noise_pips:.1f}" if noise_pips is not None else "N/A"
    # --- calculate dynamic pullback threshold ----------------------------
    recent_high = None
    recent_low = None
    try:
        highs = []
        lows = []
        for c in candles_m5[-20:]:
            if not isinstance(c, dict):
                continue
            if 'mid' in c:
                highs.append(float(c['mid']['h']))
                lows.append(float(c['mid']['l']))
            else:
                highs.append(float(c.get('h')))
                lows.append(float(c.get('l')))
        if highs and lows:
            recent_high = max(highs)
            recent_low = min(lows)
    except Exception:
        pass
    class _OneVal:
        def __init__(self, val):
            class _IL:
                def __getitem__(self, idx):
                    return val
            self.iloc = _IL()

    noise_series = _OneVal(noise_pips) if noise_pips is not None else None
    pullback_needed = calculate_dynamic_pullback({**ind_m5, 'noise': noise_series}, recent_high or 0.0, recent_low or 0.0)
    pattern_text = f"\n### Detected Chart Pattern\n{pattern_line}\n" if pattern_line else "\n### Detected Chart Pattern\nNone\n"
    # ここからAIへの英語プロンプト

    prompt = f"""
⚠️【Market Regime Classification – Flexible Criteria】
Classify as "TREND" if ANY TWO of the following conditions are met:
- ADX ≥ 20 maintained over at least the last 3 candles.
- EMA consistently sloping upwards or downwards without major reversals within the last 3 candles.
- Price consistently outside the Bollinger Band midline (above for bullish, below for bearish).

If these conditions are not clearly met, classify the market as "RANGE".

🚫【Counter-trend Trade Prohibition】
Under clearly identified TREND conditions, avoid counter-trend trades and never rely solely on RSI extremes. Treat pullbacks as trend continuation. However, if a strong reversal pattern such as a double top/bottom or head-and-shoulders is detected and ADX is turning down, a small counter-trend position is acceptable.

🔄【Counter-Trend Trade Allowance】
Allow short-term counter-trend trades only when all of the following are true:
- ADX ≤ 20 or clearly declining.
- A clear reversal pattern (double top/bottom, head-and-shoulders) is present.
- RSI ≤ 30 for LONG or ≥ 70 for SHORT, showing potential exhaustion.
- Price action has stabilized with minor reversal candles.
- TP kept small (5–10 pips) and risk tightly controlled.

📈【Trend Entry Clarification】
Once a TREND is confirmed, prioritize entries on pullbacks. Shorts enter after price rises {pullback_needed:.1f} pips above the latest low, longs after price drops {pullback_needed:.1f} pips below the latest high. This pullback rule overrides RSI extremes.

🔎【Minor Retracement Clarification】
Do not interpret short-term retracements as trend reversals. Genuine trend reversals require ALL of the following simultaneously:
- EMA direction reversal sustained for at least 3 candles.
- ADX clearly drops below 20, indicating weakening trend momentum.

🎯【Improved Exit Strategy】
Avoid exiting during normal trend pullbacks. Only exit a trend trade if **ALL** of the following are true:
- EMA reverses direction and this is sustained for at least 3 consecutive candles.
- ADX drops clearly below 20, showing momentum has faded.
If these are not all met, HOLD the position even if RSI is extreme or price briefly retraces.

♻️【Immediate Re-entry Policy】
If a stop-loss is triggered but original trend conditions remain intact (ADX≥20, clear EMA slope), immediately re-enter in the same direction upon the next valid signal.

### Recent Indicators (last 20 values each)
## M5
RSI  : {_series_tail_list(ind_m5.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_m5.get('atr'), 20)}
ADX  : {_series_tail_list(ind_m5.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_m5.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_m5.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_m5.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_m5.get('ema_slow'), 20)}

## M1
RSI  : {_series_tail_list(ind_m1.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_m1.get('atr'), 20)}
ADX  : {_series_tail_list(ind_m1.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_m1.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_m1.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_m1.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_m1.get('ema_slow'), 20)}

## D1
RSI  : {_series_tail_list(ind_d1.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_d1.get('atr'), 20)}
ADX  : {_series_tail_list(ind_d1.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_d1.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_d1.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_d1.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_d1.get('ema_slow'), 20)}

### M5 Candles
{candles_m5[-50:]}

### M1 Candles
{candles_m1[-20:]}

### D1 Candles
{candles_d1[-60:]}

{pattern_text}

### How to use the provided candles:
- Use the medium-term view (50 candles) to understand the general market trend, key support/resistance levels, and to avoid noisy, short-lived moves.
- Use the short-term view (20 candles) specifically for optimizing entry timing (such as waiting for pullbacks or breakouts) and to confirm recent price momentum.

### 90-day Historical Stats
{json.dumps(hist_stats or {}, separators=(',', ':'))}

### Estimated Noise
{noise_val} pips is the approximate short-term market noise.
Use this as a baseline for setting wider stop-loss levels.
After calculating TP hit probability, widen the SL by at least {env_loader.get_env("NOISE_SL_MULT", "1.5")} times.

### Pivot Levels
Pivot: {ind_m5.get('pivot')}, R1: {ind_m5.get('pivot_r1')}, S1: {ind_m5.get('pivot_s1')}

### N-Wave Target
{ind_m5.get('n_wave_target')}

Your task:
1. Clearly classify the current regime as "trend" or "range". If "trend", specify direction as "long" or "short". Output this at JSON key "regime".
2. Decide whether to open a trade now, strictly adhering to the above criteria. Return JSON key "entry" with: {{ "side":"long"|"short"|"no", "rationale":"…" }}
3. If side is not "no", propose TP/SL distances **in pips** along with their {TP_PROB_HOURS}-hour hit probabilities: {{ "tp_pips":int, "sl_pips":int, "tp_prob":float, "sl_prob":float }}. Output this at JSON key "risk".
   - Constraints:
     • tp_prob must be ≥ {MIN_TP_PROB:.2f}
     • Expected value (tp_pips*tp_prob - sl_pips*sl_prob) must be positive
     • (tp_pips - spread_pips) must be ≥ {env_loader.get_env("MIN_NET_TP_PIPS","2")} pips
     • If constraints are not met, set side to "no".

Respond with **one-line valid JSON** exactly as:
{{"regime":{{...}},"entry":{{...}},"risk":{{...}}}}
"""
    raw = ask_openai(prompt, model=env_loader.get_env("AI_TRADE_MODEL", "gpt-4.1-nano"))

    plan, err = parse_json_answer(raw)
    if plan is None:
        return {"entry": {"side": "no"}, "raw": raw}

    # ---- local guards -------------------------------------------------
    risk = plan.get("risk", {})
    entry = plan.get("entry", {})
    mode = entry.get("mode", "market")
    if mode not in ("market", "limit", "wait"):
        entry["mode"] = "market"
    if risk:
        try:
            tp = float(risk.get("tp_pips", 0))
            sl = float(risk.get("sl_pips", 0))
            p = float(risk.get("tp_prob", 0))
            q = float(risk.get("sl_prob", 0))
            spread = float(market_data.get("spread_pips", 0))

            noise_sl_mult = float(env_loader.get_env("NOISE_SL_MULT", "1.5"))
            sl *= noise_sl_mult
            risk["sl_pips"] = sl

            if (tp - spread) < MIN_NET_TP_PIPS:
                plan["entry"]["side"] = "no"
        except (TypeError, ValueError):
            plan["entry"]["side"] = "no"
            plan["risk"] = {}
            return plan

        if p < MIN_TP_PROB or (tp * p - sl * q) <= 0:
            plan["entry"]["side"] = "no"

    if plan.get("entry", {}).get("side") == "no":
        plan["risk"] = {}

    # Over-cool filter using Bollinger Band width and ATR
    try:
        bb_upper = ind_m5.get("bb_upper")
        bb_lower = ind_m5.get("bb_lower")
        atr_series = ind_m5.get("atr")
        if hasattr(bb_upper, "iloc"):
            bb_upper = bb_upper.iloc[-1]
        else:
            bb_upper = bb_upper[-1]
        if hasattr(bb_lower, "iloc"):
            bb_lower = bb_lower.iloc[-1]
        else:
            bb_lower = bb_lower[-1]
        if hasattr(atr_series, "iloc"):
            atr_val = float(atr_series.iloc[-1])
        else:
            atr_val = float(atr_series[-1])
        bw = float(bb_upper) - float(bb_lower)
        if (bw / atr_val) < COOL_BBWIDTH_PCT or atr_val < COOL_ATR_PCT:
            plan["entry"]["side"] = "no"
    except (TypeError, ValueError, IndexError, ZeroDivisionError):
        pass

    # ADX no-trade zone enforcement
    try:
        adx_series = ind_m5.get("adx")
        if hasattr(adx_series, "iloc"):
            adx_val = float(adx_series.iloc[-1])
        else:
            adx_val = float(adx_series[-1])
        if ADX_NO_TRADE_MIN <= adx_val <= ADX_NO_TRADE_MAX and not pattern_name:
            plan["entry"]["side"] = "no"
    except (TypeError, ValueError, IndexError):
        pass
    return plan


# ----------------------------------------------------------------------
# AI-based exit decision
# ----------------------------------------------------------------------
# Legacy evaluate_exit functionality now lives in ``exit_ai_decision``.


def should_convert_limit_to_market(context: dict) -> bool:
    """Use OpenAI to decide whether to convert a pending LIMIT to a market order."""
    prompt = (
        "We placed a limit order that has not filled and price is moving away.\n"
        f"Context: {json.dumps(context, ensure_ascii=False)}\n\n"
        "Should we cancel the limit order and place a market order instead?\n"
        "Respond with YES or NO."
    )
    try:
        result = ask_openai(prompt, model=AI_LIMIT_CONVERT_MODEL)
    except Exception as exc:
        logger.warning(f"should_convert_limit_to_market failed: {exc}")
        return False

    text = json.dumps(result) if isinstance(result, dict) else str(result)
    return text.strip().upper().startswith("YES")



logger.info("OpenAI Analysis finished")

# Exports
__all__ = [
    "get_ai_cooldown_sec",
    "get_entry_decision",
    "get_exit_decision",
    "get_tp_sl_adjustment",
    "get_market_condition",
    "get_trade_plan",
    "AIDecision",
    "evaluate_exit",
    "should_convert_limit_to_market",
    "LIMIT_THRESHOLD_ATR_RATIO",
    "MAX_LIMIT_AGE_SEC",
    "MIN_NET_TP_PIPS",
    "COOL_BBWIDTH_PCT",
    "COOL_ATR_PCT",
    "ADX_NO_TRADE_MIN",
    "ADX_NO_TRADE_MAX",
    "EXIT_BIAS_FACTOR",
    "LOCAL_WEIGHT_THRESHOLD",
    "calc_consistency",
]
