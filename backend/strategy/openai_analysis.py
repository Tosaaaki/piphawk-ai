import logging
import json
from backend.utils.openai_client import ask_openai
from backend.utils import env_loader, parse_json_answer
from backend.strategy.pattern_ai_detection import detect_chart_pattern

# When true, use local pattern scanner instead of OpenAI
USE_LOCAL_PATTERN = env_loader.get_env("USE_LOCAL_PATTERN", "false").lower() == "true"

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
AI_LIMIT_CONVERT_MODEL: str = env_loader.get_env("AI_LIMIT_CONVERT_MODEL", "gpt-4o-mini")

# --- Volatility and ADX filters ---
COOL_BBWIDTH_PCT: float = float(env_loader.get_env("COOL_BBWIDTH_PCT", "0"))
COOL_ATR_PCT: float = float(env_loader.get_env("COOL_ATR_PCT", "0"))
ADX_NO_TRADE_MIN: float = float(env_loader.get_env("ADX_NO_TRADE_MIN", "20"))
ADX_NO_TRADE_MAX: float = float(env_loader.get_env("ADX_NO_TRADE_MAX", "30"))
USE_LOCAL_PATTERN: bool = (
    env_loader.get_env("USE_LOCAL_PATTERN", "false").lower() == "true"
)

# Global variables to store last AI call timestamps
_last_entry_ai_call_time = 0.0
_last_exit_ai_call_time = 0.0
# Regime‑AI cache
_last_regime_ai_call_time = 0.0
_cached_regime_result: dict | None = None

def get_ai_cooldown_sec(current_position: dict | None) -> int:
    """
    Return the appropriate cooldown seconds depending on whether we are flat
    or holding an open position.
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
            return AI_COOLDOWN_SEC_OPEN
    return AI_COOLDOWN_SEC_FLAT

logger = logging.getLogger(__name__)

logger.info("OpenAI Analysis started")



# ----------------------------------------------------------------------
# Market‑regime classification helper (OpenAI direct, enhanced English prompt)
# ----------------------------------------------------------------------
def get_market_condition(context: dict) -> str:
    prompt = (
        "Based on the current market data and indicators provided below, determine whether the market is in a 'trend' or 'range' state.\n\n"
        "### Evaluation Criteria:\n"
        "- Short-term price action: consecutive candles strongly moving in one direction suggest a trend.\n"
        "- EMA slope and price relationship: prices consistently above or below EMA indicate a trending market.\n"
        "- ADX value: a value above 25 typically indicates a trending market.\n"
        "- RSI extremes: extremely low or high RSI values can suggest range-bound conditions but must be evaluated alongside short-term price movements.\n\n"
        "If RSI stays consistently near or below 30 for multiple candles, this indicates a strong bearish (downward) trend rather than oversold range conditions.\n"
        "Conversely, if RSI stays consistently near or above 70 for multiple candles, this indicates a strong bullish (upward) trend rather than overbought range conditions.\n"
        f"### Market Data and Indicators:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        "Respond strictly with either 'trend' or 'range'."
    )
    response = ask_openai(prompt).strip().lower()
    return response if response in ['trend', 'range'] else 'range'


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
        return json.dumps({"action": "HOLD", "reason": "Cooldown active"})

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
    unreal_pnl = current_position.get("unrealized_pl", "N/A")

    secs_since_entry = market_data.get("secs_since_entry")
    pips_from_entry = market_data.get("pips_from_entry")

    if secs_since_entry is None:
        try:
            entry_time_str = current_position.get("entry_time") or current_position.get("openTime")
            if entry_time_str:
                entry_dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                secs_since_entry = (datetime.utcnow() - entry_dt).total_seconds()
        except Exception:
            secs_since_entry = None

    # --------------------------------------------------------------
    # Break‑even trigger
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
        "You are an expert FX trader AI. Your job is to decide, with clear and concise reasoning, whether to HOLD or EXIT an open position based on the latest market context and indicators.\n\n"
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
    response = ask_openai(prompt)
    _last_exit_ai_call_time = now
    logger.debug(f"[get_exit_decision] prompt sent:\n{prompt}")
    logger.info(f"OpenAI response: {response}")

    # 返値が dict ならそのまま、文字列なら JSON とみなしてパース
    if isinstance(response, dict):
        response_json = response
    else:
        try:
            response_json = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Invalid JSON: {response}")
            return json.dumps({"action": "HOLD", "reason": "Invalid response format"})

    return json.dumps(response_json)



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
    pattern_text = f"\n### Detected Chart Pattern\n{pattern_line}\n" if pattern_line else "\n### Detected Chart Pattern\nNone\n"

    prompt = f"""
⚠️【Market Regime Classification – Flexible Criteria】
Classify as "TREND" if ANY TWO of the following conditions are met:
- ADX ≥ 20 maintained over at least the last 3 candles.
- EMA consistently sloping upwards or downwards without major reversals within the last 3 candles.
- Price consistently outside the Bollinger Band midline (above for bullish, below for bearish).

If these conditions are not clearly met, classify the market as "RANGE".

🚫【Counter-trend Trade Prohibition】
Under clearly identified TREND conditions, strictly prohibit any counter-trend trades. Never initiate trades solely based on RSI extremes if trend conditions are met.

🔄【Counter-Trend Trade Allowance】
Allow short-term counter-trend trades ONLY when ALL of the following conditions are met:
- ADX ≤ 20 or clearly declining.
- RSI ≤ 30 for LONG entries or ≥ 70 for SHORT entries, indicating potential exhaustion.
- Price action shows clear signs of stabilization (e.g., price stopped making new highs/lows, minor reversal candles present).
- TP set very conservatively (5-10 pips) with strict risk control.

📈【Trend Entry Clarification】
When a TREND is identified (using the above criteria), allow new entries even if RSI is overbought (>70 for longs) or oversold (<30 for shorts), **as long as other indicators confirm the trend is likely to continue**. Do NOT block entries just because RSI is extreme if the EMA slope, ADX, and price action all confirm trend continuation. Shorts must enter on pullbacks at least 5 pips above the latest low. Longs must enter on pullbacks at least 5 pips below the latest high.

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
RSI  : {ind_m5.get('rsi', [])[-20:]}
ATR  : {ind_m5.get('atr', [])[-20:]}
ADX  : {ind_m5.get('adx', [])[-20:]}
BB_hi: {ind_m5.get('bb_upper', [])[-20:]}
BB_lo: {ind_m5.get('bb_lower', [])[-20:]}
EMA_f: {ind_m5.get('ema_fast', [])[-20:]}
EMA_s: {ind_m5.get('ema_slow', [])[-20:]}

## M1
RSI  : {ind_m1.get('rsi', [])[-20:]}
ATR  : {ind_m1.get('atr', [])[-20:]}
ADX  : {ind_m1.get('adx', [])[-20:]}
BB_hi: {ind_m1.get('bb_upper', [])[-20:]}
BB_lo: {ind_m1.get('bb_lower', [])[-20:]}
EMA_f: {ind_m1.get('ema_fast', [])[-20:]}
EMA_s: {ind_m1.get('ema_slow', [])[-20:]}

## D1
RSI  : {ind_d1.get('rsi', [])[-20:]}
ATR  : {ind_d1.get('atr', [])[-20:]}
ADX  : {ind_d1.get('adx', [])[-20:]}
BB_hi: {ind_d1.get('bb_upper', [])[-20:]}
BB_lo: {ind_d1.get('bb_lower', [])[-20:]}
EMA_f: {ind_d1.get('ema_fast', [])[-20:]}
EMA_s: {ind_d1.get('ema_slow', [])[-20:]}

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

### 想定ノイズ (Estimated Noise)
{noise_val} pips is the approximate short-term market noise.
Use this as a baseline for setting wider stop-loss levels.

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
    raw = ask_openai(prompt, model=env_loader.get_env("AI_TRADE_MODEL", "gpt-4o-mini"))

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
            p  = float(risk.get("tp_prob", 0))
            q  = float(risk.get("sl_prob", 0))
            spread = float(market_data.get("spread_pips", 0))
            if (tp - spread) < MIN_NET_TP_PIPS:
                plan["entry"]["side"] = "no"
        except (TypeError, ValueError):
            plan["entry"]["side"] = "no"
            return plan

        if p < MIN_TP_PROB or (tp * p - sl * q) <= 0:
            plan["entry"]["side"] = "no"

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
        if ADX_NO_TRADE_MIN <= adx_val <= ADX_NO_TRADE_MAX:
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

    if isinstance(result, dict):
        text = json.dumps(result)
    else:
        text = str(result)
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
]
