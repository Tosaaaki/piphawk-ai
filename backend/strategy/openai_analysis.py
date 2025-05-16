import logging
import json
import pandas as pd
from backend.utils.openai_client import ask_openai
import os
import math
# --- Added for AI-based exit decision ---
import os
from dataclasses import dataclass
from typing import Any, Dict
import time

# ----------------------------------------------------------------------
# Config – driven by environment variables
# ----------------------------------------------------------------------
AI_COOLDOWN_SEC_FLAT: int = int(os.getenv("AI_COOLDOWN_SEC_FLAT", 60))
AI_COOLDOWN_SEC_OPEN: int = int(os.getenv("AI_COOLDOWN_SEC_OPEN", 30))
BREAKEVEN_TRIGGER_PIPS: int = int(os.getenv("BREAKEVEN_TRIGGER_PIPS", 4))

# Global variables to store last AI call timestamps
_last_entry_ai_call_time = 0.0
_last_exit_ai_call_time = 0.0

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
# Entry decision
# ----------------------------------------------------------------------
def get_entry_decision(market_data, strategy_params, indicators=None, higher_tf=None):
    """
    Ask the LLM whether we should open a new trade now.

    Returns a Python dict like:
        {"side":"long","tp_pips":30,"sl_pips":15}
        {"side":"short","tp_pips":25,"sl_pips":10}
        {"side":"no"}

    higher_tf (dict|None): higher‑timeframe reference levels
    """
    global _last_entry_ai_call_time
    now = time.time()
    cooldown = get_ai_cooldown_sec(None)
    if now - _last_entry_ai_call_time < cooldown:
        return {"side": "no"}

    if indicators is None:
        indicators = {}

    market_data_json = json.dumps(market_data)
    strategy_params_json = json.dumps(strategy_params)

    def convert_to_json_serializable(obj):
        if isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        raise TypeError(f"Type {type(obj)} not serializable")

    indicators_json = json.dumps(indicators, default=convert_to_json_serializable)

    higher_tf_json = json.dumps(higher_tf) if higher_tf else "{}"

    prompt = f"""
You are a seasoned FX trader assistant. Based on the following inputs, decide if a new trade should be opened right now.

First determine the market regime: classify as "RANGE" (sideways) or "TREND" (directional) based on ADX, Bollinger Bands, and moving averages.
If RANGE: identify support and resistance (e.g. Bollinger Band lower/upper) and suggest entries at band extremes when RSI is oversold/overbought.
If TREND: identify direction via moving average cross (e.g. EMA fast vs. slow) and suggest entries in the trend direction on pullbacks to EMA or mid-band.

Market data: {market_data_json}
Strategy parameters: {strategy_params_json}
Technical indicators: {indicators_json}
Higher‑timeframe reference levels: {higher_tf_json}
- Daily pivot point (pivot_d) and its ±5 pips buffer: avoid entries when price is within this range.
- 4H pivot point (pivot_h4) and support/resistance levels: treat similarly to daily pivot.
- Consider higher‑timeframe trend direction: if daily trend opposes the proposed side, prefer "no" or "wait_pullback".

Carefully analyze the market context and indicators.

Regime-specific guidance:
- **RANGE**: Look for entries at Bollinger Band extremes. 
  • For long entries: price near lower band with RSI ≤ 30.  
  • For short entries: price near upper band with RSI ≥ 70.  
  Use Bollinger Bands and RSI extremes only when the regime is confirmed as RANGE.
- **TREND**: Identify trend direction by EMA fast crossing EMA slow.  
  • For long trend: EMA fast > EMA slow and price pullback to EMA fast or mid-band.  
  • For short trend: EMA fast < EMA slow and price pullback to EMA fast or mid-band.

Do NOT open counter-trend trades when price is within ±5 pips of a daily or 4H pivot.
- Dynamically set TP and SL considering market volatility, key technical levels, and risk-reward balance.
- When proposing **"tp_pips"**, explicitly factor in:
    • **Volatility** – use the latest ATR; aim for TP ≈ 2‑3 × ATR.  
    • **Bollinger Band** distances – for trend‑following trades, allow up to 80 % of BB width.  
    • **RSI reversion** – if RSI is extreme (≤35 / ≥65), set TP so that RSI would likely revert toward 50 at exit.  
  Ensure risk‑reward ≥ 1.5 and round TP/SL to whole pips.

  - Avoid “chasing” the same price:  
    • If we have just closed a trade in the **same direction** within the last 5 minutes **OR**  
      the current price is within **5 pips** of that exit level, prefer `"wait_pullback": true` or `"side":"no"`.  
  - For **short** ideas, prefer to wait until price bounces at least **30–50 % of the last down‑leg**  
    (e.g. mid‑Bollinger or EMA‑20) before re‑entering, **unless** momentum is extreme (ADX > 25 **and** ATR is high).  
  
Please respond strictly in JSON format with these keys only:
- "side": "long", "short", or "no"
- "tp_pips": take profit in pips (integer ≥ 1), omit or set to null if "side" is "no"
- "sl_pips": stop loss in pips (integer ≥ 1), omit or set to null if "side" is "no"

Examples:
{{"side":"long","tp_pips":25,"sl_pips":12}}
{{"side":"short","tp_pips":20,"sl_pips":10}}
{{"side":"no"}}

Do NOT include any extra text, fields, or reasoning.
"""
    response = ask_openai(prompt)
    _last_entry_ai_call_time = now
    import re
    response_clean = re.sub(r'```(?:json)?|```', '', response).strip()
    response = response_clean
    logger.info(f"OpenAI response: {response}")

    if isinstance(response, dict):
        return response
    try:
        parsed = json.loads(response)
        if parsed.get("side") not in ("long", "short"):
            return {"side": "no"}

        # ── 反転オプション ───────────────────────────────────────────────
        # INVERT_ENTRY_SIDE=true のとき、long⇔shortを入れ替える
        if os.getenv("INVERT_ENTRY_SIDE", "false").lower() == "true":
            if parsed["side"] == "long":
                parsed["side"] = "short"
            elif parsed["side"] == "short":
                parsed["side"] = "long"

        return parsed
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse OpenAI response: {e}")
        return {"side": "no"}



# ----------------------------------------------------------------------
# Exit decision
# ----------------------------------------------------------------------
def get_exit_decision(market_data, current_position, indicators=None, higher_tf=None):
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
    """
    Ask the LLM whether current TP / SL should be adjusted.
    Returns the raw response (string or dict as generated by LLM).
    """
    prompt = f"""
    Given the current market data:
    {market_data}
    and the current take profit (TP): {current_tp}
    and stop loss (SL): {current_sl}
    Should we adjust the TP or SL? If yes, provide new TP and SL values.
    Otherwise, say "No adjustment".
    """
    response = ask_openai(prompt)
    logger.info(f"OpenAI response: {response}")
    return response  # ← そのまま返す


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
    model = os.getenv("AI_EXIT_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("AI_EXIT_TEMPERATURE", "0.0"))
    max_tokens = int(os.getenv("AI_EXIT_MAX_TOKENS", "128"))
    raw = ask_openai(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
    return _exit_parse_answer(raw)


print("[INFO] OpenAI Analysis finished")

# Exports
__all__ = [
    "get_ai_cooldown_sec",
    "get_entry_decision",
    "get_exit_decision",
    "get_tp_sl_adjustment",
    "AIDecision",
    "evaluate_exit",
]