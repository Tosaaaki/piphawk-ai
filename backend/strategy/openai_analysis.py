import logging
import json
from backend.utils.openai_client import ask_openai
from backend.utils import env_loader
# --- Added for AI-based exit decision ---
from dataclasses import dataclass
from typing import Any, Dict
import time

# ----------------------------------------------------------------------
# Config – driven by environment variables
# ----------------------------------------------------------------------
AI_COOLDOWN_SEC_FLAT: int = int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", 60))
AI_COOLDOWN_SEC_OPEN: int = int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", 30))
# Regime‑classification specific cooldown (defaults to flat cooldown)
AI_REGIME_COOLDOWN_SEC: int = int(env_loader.get_env("AI_REGIME_COOLDOWN_SEC", AI_COOLDOWN_SEC_FLAT))

# --- Threshold for AI‑proposed TP probability ---
MIN_TP_PROB: float = float(env_loader.get_env("MIN_TP_PROB", "0.75"))
LIMIT_THRESHOLD_ATR_RATIO: float = float(env_loader.get_env("LIMIT_THRESHOLD_ATR_RATIO", "0.3"))
MAX_LIMIT_AGE_SEC: int = int(env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))
MIN_NET_TP_PIPS: float = float(env_loader.get_env("MIN_NET_TP_PIPS", "2"))
BREAKEVEN_TRIGGER_PIPS: int = int(env_loader.get_env("BREAKEVEN_TRIGGER_PIPS", 4))

# --- Volatility and ADX filters ---
COOL_BBWIDTH_PCT: float = float(env_loader.get_env("COOL_BBWIDTH_PCT", "0"))
COOL_ATR_PCT: float = float(env_loader.get_env("COOL_ATR_PCT", "0"))
ADX_NO_TRADE_MIN: float = float(env_loader.get_env("ADX_NO_TRADE_MIN", "20"))
ADX_NO_TRADE_MAX: float = float(env_loader.get_env("ADX_NO_TRADE_MAX", "30"))

# Global variables to store last AI call timestamps
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
    if (
        current_position
        and abs(float(current_position.get("units", 0))) > 0
    ):
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
def get_entry_decision(market_data, strategy_params, indicators=None, candles=None, market_cond=None, higher_tf=None):
    plan = get_trade_plan(market_data, indicators or {}, candles or [], strategy_params)
    return plan.get("entry", {"side": "no"})



# ----------------------------------------------------------------------
# Exit decision
# ----------------------------------------------------------------------
def get_exit_decision(market_data, current_position,
                      indicators=None, entry_regime=None,
                      market_cond=None, higher_tf=None):
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

    # --------------------------------------------------------------
    # Break‑even trigger
    # --------------------------------------------------------------
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

    breakeven_reached = pips_from_entry >= BREAKEVEN_TRIGGER_PIPS

    prompt = (
        "You are an expert FX trader tasked with making precise decisions on whether to HOLD or EXIT an existing trade.\n\n"
        f"## Current Position Side: {side}\n\n"
        "## Steps for Analysis\n"
        "1. Classify the market condition clearly as either 'range' or 'trend' using ADX, RSI, EMA, and Bollinger Bands.\n"
        "   - Trend: ADX > 25, clear EMA slope, price consistently in upper or lower Bollinger half.\n"
        "   - Range: ADX < 25, neutral EMA, price oscillating around Bollinger midline.\n"
        "\n"
        "2. Decision Criteria based on current position:\n"
        "   - If LONG:\n"
        "     - HOLD if indicators (EMA slope upwards, ADX >25, price upper Bollinger) suggest continued upward momentum.\n"
        "     - EXIT if RSI >70 and price showing weakness at Bollinger upper limit, or indicators weakening.\n"
        "\n"
        "   - If SHORT:\n"
        "     - HOLD if indicators (EMA slope downwards, ADX >25, price lower Bollinger) suggest continued downward momentum.\n"
        "     - EXIT if RSI <30 and price bouncing at Bollinger lower limit, or indicators strengthening upwards.\n"
        "\n"
        "3. Post-entry Stability:\n"
        "   - Avoid immediate exits just after entry for minor fluctuations. Wait at least 5 minutes or a ±5 pip move before considering EXIT.\n"
        "\n"
        "## Indicators Reference:\n"
        "- ADX (Trend strength: >25 strong, <25 weak/range)\n"
        "- RSI (Overbought >70, Oversold <30)\n"
        "- EMA (Trend direction and strength)\n"
        "- Bollinger Bands (Market volatility and extremes)\n"
        "\n"
        "## Response Format (strict JSON):\n"
        "{\"action\":\"EXIT or HOLD\",\"reason\":\"Concise, insightful reason under 25 words\"}\n"
        "\n"
        "Example responses:\n"
        "{\"action\":\"HOLD\",\"reason\":\"Upward EMA slope, strong ADX indicates potential further gains.\"}\n"
        "{\"action\":\"EXIT\",\"reason\":\"RSI overbought with weakening price momentum, securing profits.\"}\n"
        "\n"
        "No other text or explanation."
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
    indicators: dict,
    candles: list[dict],
    hist_stats: dict | None = None,
) -> dict:
    """
    Single‑shot call to the LLM that returns a dict:
        {
          "regime": {...},
          "entry":  {...},
          "risk":   {...}
        }
    The function also performs local guards:
        • tp_prob ≥ MIN_TP_PROB
        • expected value (tp*tp_prob – sl*sl_prob) > 0
      If either guard fails, it forces side:"no".
    """
    prompt = f"""
You are an elite FX trader and quantitative analyst.

### Task
1️⃣  Classify the current regime as "trend" or "range".
    If "trend", include direction "long" or "short".  
    Return this at JSON key "regime".

🚩 **Regime‑specific entry rules**
   • range : prefer mean‑reversion trades  
       – go LONG near lower Bollinger band when RSI ≤ 30  
       – go SHORT near upper Bollinger band when RSI ≥ 70  
       – target TP = middle band or opposite band; SL = band outside + ATR×0.8  
   • trend : enter only in trend direction on healthy pullbacks  
       – use EMA_fast vs EMA_slow cross & ADX>25 to confirm
       – TP ≈ 1.5–2.5 × ATR in trend direction

⚠️ **Short Entry at Resistance or Market Top**
   – If price is near a strong resistance level or a clear market top, especially after a rapid upward movement, prioritize entering short positions.
   – When entering short after such conditions, set the take-profit (TP) target near realistic pullback limits, not overly ambitious, to capture likely retracement.

Conversely, if the price is near a strong support level or a clear market bottom, especially after a rapid downward movement, prioritize entering long positions. Set the take-profit (TP) target near realistic bounce-back limits to capture likely retracement effectively.

⚙️ **Additional filters**
   – Over‑cool filter: skip trades when BB width/ATR < {COOL_BBWIDTH_PCT} or ATR < {COOL_ATR_PCT}
   – ADX no‑trade zone {ADX_NO_TRADE_MIN}–{ADX_NO_TRADE_MAX}
   – BB‑width scaled TP/SL
   – Dynamic RSI thresholds
   – Limit‑only mode when range is narrow
   – When the market has clearly dropped significantly and is close to recent historical lows or support levels, refrain from entering short positions. Conversely, when the market has risen significantly and is near recent historical highs or resistance levels, refrain from entering long positions. This helps to avoid trades at extreme levels that have higher reversal risk.
   - Avoid entering short positions immediately after a significant rapid price drop, especially when RSI is persistently oversold (≤30) and prices approach strong historical support or recent market lows. Conversely, avoid entering long positions immediately after a significant rapid price rise when RSI is persistently overbought (≥70) and prices approach strong historical resistance or recent market highs. This is critical to reduce risk from sharp reversal movements.

⚠️【Special Rules for RSI Extremes】
Even if RSI is at extreme levels (≤ 30 oversold or ≥ 70 overbought), it is acceptable to pursue entries aggressively under the following conditions:
- ADX clearly exceeds 25, indicating a strong trend.
- EMA shows a consistent slope, confirming continued momentum in the trend direction.
- Price forms consecutive strong candles in one direction, accelerating the trend.

However, refrain from entering trades at RSI extremes under these conditions:
- ADX is below or equal to 25, indicating an unclear or weak trend.
- EMA is flat or trending in the opposite direction.
- Price action is unstable, lacking a clear directional bias.
- Multiple small counter-trend bounces are observed over recent candles.

Special RSI and Trend Rule:
  - If RSI ≤ 30 and price action shows at least 3 consecutive bearish candles with progressively lower closes and lower highs, along with a negative EMA slope for at least 5 recent candles, and an ADX above 25, prioritize entering short positions.
  - Conversely, if RSI ≥ 70 and price action shows at least 3 consecutive bullish candles with progressively higher closes and higher lows, along with a positive EMA slope for at least 5 recent candles, and an ADX above 25, prioritize entering long positions.
  - Otherwise, do not make entry decisions solely based on RSI being oversold or overbought.

Define "strong resistance" as:
  - Price has been rejected at least twice at similar price levels within the last 20 candles.
  - Presence of reversal candle patterns (e.g., pin bars, engulfing patterns).

Define "strong support" as:
  - Price has bounced at least twice at similar price levels within the last 20 candles.
  - Presence of bullish reversal patterns (e.g., hammer candles, engulfing patterns).

Do NOT enter a trade if:
  - Indicators provide conflicting signals.
  - Market is within ADX no-trade zone ({ADX_NO_TRADE_MIN}-{ADX_NO_TRADE_MAX}).
  - Price action is indecisive (small candle bodies, long wicks).

4️⃣  If RSI is satisfied but EMA／BB alignment is pending, choose:
    • mode:"limit" with limit_price at EMA_fast, EMA_slow, or BB_mid  
    • mode:"wait"  if distance &lt; 0.1 × ATR (just re‑evaluate next loop)  
    When mode is "limit", set valid_for_sec ≤ {MAX_LIMIT_AGE_SEC}.  

4️⃣  Decide whether to open a trade *now*.  
    Return JSON key "entry" with:
        {{ "side":"long"|"short"|"no", "rationale":"…" }}

5️⃣  If side ≠ "no", propose TP/SL distances **in pips** plus
    their 24‑hour hit probabilities:
        {{ "tp_pips":int, "sl_pips":int,
           "tp_prob":float, "sl_prob":float }}
    Return this at JSON key "risk".

    **Constraints**
      • tp_prob must be ≥ {MIN_TP_PROB:.2f}
      • expected value (tp_pips*tp_prob - sl_pips*sl_prob) must be > 0
      • If you cannot satisfy both, output side:"no".
      • (tp_pips - spread_pips) must be ≥ {env_loader.get_env("MIN_NET_TP_PIPS","2")} pips

### Recent indicators (last 20 values each)
RSI  : {indicators.get('rsi', [])[-20:]}
ATR  : {indicators.get('atr', [])[-20:]}
ADX  : {indicators.get('adx', [])[-20:]}
BB_hi: {indicators.get('bb_upper', [])[-20:]}
BB_lo: {indicators.get('bb_lower', [])[-20:]}
EMA_f: {indicators.get('ema_fast', [])[-20:]}
EMA_s: {indicators.get('ema_slow', [])[-20:]}

### Candles (last 20, OANDA format)
{candles[-20:]}

### 90‑day historical stats
{json.dumps(hist_stats or {}, separators=(',', ':'))}

Special rules:
- If RSI remains flat at the upper or lower extremes, clearly classify the market as trending.
- If RSI remains consistently flat around 30 or 70 and price action shows consecutive directional movements, classify the market as trending, not ranging.

- Emphasize the RSI trend direction (rising or falling), not only the absolute value.
- Prioritize entries if MACD forms a clear golden cross (MACD line crossing above the signal line).
- Clearly indicate when the price rebounds off significant Bollinger Band levels, especially the ±2σ lines, as strong entry signals.

Trend recognition conditions:
- If RSI ≤ 30 and there are at least 3 consecutive bearish candles with progressively lower closes and highs, along with a downward EMA slope sustained for at least 5 candles, classify as a downward trend.
- If RSI ≥ 70 and there are at least 3 consecutive bullish candles with progressively higher closes and lows, along with an upward EMA slope sustained for at least 5 candles, classify as an upward trend.

Prioritize these rules for market regime determination, especially to avoid misclassification as ranging when RSI is flat at extreme values.

⚠️【Entry Improvement for Continued Trends at RSI Extremes】
- Even if RSI ≤ 30 (oversold), strongly prioritize entering SHORT trades if all these conditions hold:
  - ADX remains consistently above 25, clearly signaling strong momentum.
  - EMA slope is consistently downward over at least the last 5 candles.
  - Recent price action shows at least 3 consecutive bearish candles with progressively lower closes and highs.
- Conversely, even if RSI ≥ 70 (overbought), strongly prioritize entering LONG trades if:
  - ADX remains consistently above 25, clearly signaling strong momentum.
  - EMA slope is consistently upward over at least the last 5 candles.
  - Recent price action shows at least 3 consecutive bullish candles with progressively higher closes and lows.
  
Under these conditions, override typical RSI hesitation and confidently execute entries in the direction of the clear trend to maximize profit opportunities.

Respond **one‑line valid JSON** exactly:
{{"regime":{{...}},"entry":{{...}},"risk":{{...}}}}
"""
    raw = ask_openai(prompt, model=env_loader.get_env("AI_TRADE_MODEL", "gpt-4o-mini"))
    if isinstance(raw, dict):
        plan = raw
    else:
        try:
            plan = json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.error("Invalid JSON from LLM → fallback no‑trade")
            return {"entry": {"side": "no"}}

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
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        atr_series = indicators.get("atr")
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
        adx_series = indicators.get("adx")
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
# AI-based exit decision using AIDecision
# ----------------------------------------------------------------------
_EXIT_SYSTEM_PROMPT = (
    "You are an expert foreign‑exchange risk manager and trading coach. "
    "Given the current trading context you must respond with a strict JSON "
    "object using exactly the keys: action, confidence, reason.\n\n"
    "Allowed values for *action* are EXIT, HOLD, SCALE.\n"
    "*confidence* must be a number between 0 and 1.\n"
    "*reason* must be a single short English sentence (max 25 words).\n"
    "Do not wrap the JSON in markdown."
)
_EXIT_ALLOWED_ACTIONS = {"EXIT", "HOLD", "SCALE"}

@dataclass(slots=True)
class AIDecision:
    action: str = "HOLD"
    confidence: float = 0.0
    reason: str = ""
    def as_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "confidence": self.confidence, "reason": self.reason}

def _exit_build_prompt(context: Dict[str, Any]) -> str:
    user_json = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    return f"{_EXIT_SYSTEM_PROMPT}\nUSER_CONTEXT:\n{user_json}"

def _exit_parse_answer(raw: str | dict) -> AIDecision:
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            return AIDecision(action="HOLD", confidence=0.0, reason=f"json_error:{exc}")
    action = str(data.get("action", "HOLD")).upper()
    if action not in _EXIT_ALLOWED_ACTIONS:
        action = "HOLD"
    try:
        conf = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    reason = str(data.get("reason", ""))[:120]
    return AIDecision(action=action, confidence=conf, reason=reason)

def evaluate_exit(context: Dict[str, Any]) -> AIDecision:
    """
    Ask OpenAI whether to exit a position given the context.
    Returns an AIDecision(action, confidence, reason).
    """
    prompt = _exit_build_prompt(context)
    model = env_loader.get_env("AI_EXIT_MODEL", "gpt-4o-mini")
    temperature = float(env_loader.get_env("AI_EXIT_TEMPERATURE", "0.0"))
    max_tokens = int(env_loader.get_env("AI_EXIT_MAX_TOKENS", "128"))
    raw = ask_openai(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
    return _exit_parse_answer(raw)


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
    "LIMIT_THRESHOLD_ATR_RATIO",
    "MAX_LIMIT_AGE_SEC",
    "MIN_NET_TP_PIPS",
    "COOL_BBWIDTH_PCT",
    "COOL_ATR_PCT",
    "ADX_NO_TRADE_MIN",
    "ADX_NO_TRADE_MAX",
]
