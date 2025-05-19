import logging
import json
import pandas as pd
from backend.utils.openai_client import ask_openai
from backend.utils import env_loader
import math
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
ENTRY_COOLDOWN_SEC_AFTER_CLOSE: int = int(env_loader.get_env("ENTRY_COOLDOWN_SEC_AFTER_CLOSE", 300))

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
# Global variable to store last position close time (for entry cooldown after close)
_last_position_close_time = 0.0

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

print("[INFO] OpenAI Analysis started")


# ----------------------------------------------------------------------
# Market‑regime classification helper
# ----------------------------------------------------------------------
def get_market_condition(indicators: dict, candles: list[dict]) -> dict:
    plan = get_trade_plan({}, indicators, candles)
    return plan.get("regime", {"market_condition": "unclear"})


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

    prompt = f"""
You are an expert FX trader making sophisticated and flexible decisions about whether to EXIT (close) or HOLD an **existing trade**.

## Position
• SIDE            : **{side}**
• SIZE (units)    : {current_position.get("units")}
• AVG ENTRY PRICE : {current_position.get("average_price")}
• UNREALIZED P/L  : {unreal_pnl} JPY
• B/E TRIGGER     : {"YES" if breakeven_reached else "NO"} (>{BREAKEVEN_TRIGGER_PIPS} pips)

## Decision Guidelines
- Carefully analyze the technical indicators and current market context.
- Consider market momentum, trend strength, potential reversals, and key support/resistance levels.
- Prioritize securing profit, but also allow reasonable fluctuations if there's potential for greater profit.
- **Regime‑shift awareness**: Use ADX (25 threshold) and Bollinger‑Band width to detect if the market has switched between *range* and *trend*.  
  • If the new regime is favorable to the current position (e.g., a fresh trend in the trade direction), prefer **HOLD** to ride profits.  
  • If the new regime increases risk (e.g., range compression against an existing trend position), prefer **EXIT** quickly.
- Consider the entry regime type (TREND or RANGE) used when opening the position:
  • For TREND entries, aim to exit at appropriate trend profit levels, respecting trend momentum and pullbacks.
  • For RANGE entries, use Bollinger Bands and RSI extremes to guide exit levels, taking profits near band extremes or on RSI reversion.

## Market Snapshot
{market_data}

## Higher‑TF reference
{higher_tf_json}

## AI‑derived market condition
{market_cond_json}

## Entry‑regime at position open
{entry_regime_json}

## Technical Indicators (JSON)
{indicators}

## Response format (exactly one line of valid JSON)
Return a JSON object with keys:
  - "action": either "EXIT" or "HOLD"
  - "reason": a concise, insightful explanation for your decision

Examples:
  {{"action":"EXIT", "reason":"RSI signals overbought and price approaching strong resistance"}}
  {{"action":"HOLD", "reason":"Trend remains strong and indicators suggest continued momentum"}}

Do NOT output anything else (no prefixes, no Markdown, no reasoning).
"""
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

⚙️ **Additional filters**
   – Over‑cool filter: skip trades when BB width/ATR < {COOL_BBWIDTH_PCT} or ATR < {COOL_ATR_PCT}
   – ADX no‑trade zone {ADX_NO_TRADE_MIN}–{ADX_NO_TRADE_MAX}
   – BB‑width scaled TP/SL
   – Dynamic RSI thresholds
   – Limit‑only mode when range is narrow

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

Respond **one‑line valid JSON** exactly:
{{"regime":{{...}},"entry":{{...}},"risk":{{...}}}}
"""
    raw = ask_openai(prompt, model=env_loader.get_env("AI_TRADE_MODEL", "gpt-4o-mini"))
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
        bw = float(indicators.get("bb_upper")[-1]) - float(indicators.get("bb_lower")[-1])
        atr_val = float(indicators.get("atr")[-1])
        if (bw / atr_val) < COOL_BBWIDTH_PCT or atr_val < COOL_ATR_PCT:
            plan["entry"]["side"] = "no"
    except (TypeError, ValueError, IndexError, ZeroDivisionError):
        pass

    # ADX no-trade zone enforcement
    try:
        adx_val = float(indicators.get("adx")[-1])
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

def _exit_parse_answer(raw: str) -> AIDecision:
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


print("[INFO] OpenAI Analysis finished")

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
