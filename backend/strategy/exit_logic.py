from typing import Dict, Any
from backend.strategy.openai_analysis import get_exit_decision
from backend.orders.order_manager import OrderManager
from backend.logs.log_manager import log_trade
from datetime import datetime
import logging
import os
# Trailing‑stop configuration
TRAIL_TRIGGER_PIPS = float(os.getenv("TRAIL_TRIGGER_PIPS", "10"))  # profit threshold to arm trailing stop
TRAIL_DISTANCE_PIPS = float(os.getenv("TRAIL_DISTANCE_PIPS", "6"))  # distance of the trailing stop itself
# Toggle for enabling/disabling trailing‑stop logic
TRAIL_ENABLED = os.getenv("TRAIL_ENABLED", "true").lower() == "true"

# --- Early‑exit & breakeven settings ------------------------------------
EARLY_EXIT_ENABLED    = os.getenv("EARLY_EXIT_ENABLED", "true").lower() == "true"
BREAKEVEN_BUFFER_PIPS = float(os.getenv("BREAKEVEN_BUFFER_PIPS", "2"))  # pips offset from BE

# Dynamic ATR‑based trailing‑stop (always enabled)
TRAIL_TRIGGER_MULTIPLIER  = float(os.getenv("TRAIL_TRIGGER_MULTIPLIER", "1.2"))
TRAIL_DISTANCE_MULTIPLIER = float(os.getenv("TRAIL_DISTANCE_MULTIPLIER", "1.0"))
from backend.orders.position_manager import get_position_details
import re
import json

order_manager = OrderManager()

def generate_position_condition_prompt(position: Dict[str, Any], market_data: Dict[str, Any], indicators: Dict[str, Any]) -> str:
    """
    Generate a prompt describing the current position, market data, and indicators for AI analysis.
    """
    prompt = (
        "Current position details:\n"
        f"{position}\n\n"
        "Recent market data:\n"
        f"{market_data}\n\n"
        "Indicator values:\n"
        f"{indicators}\n\n"
        "Given the above, should the position be exited now? Reply with 'EXIT' or 'HOLD' and a very brief explanation."
    )
    return prompt


def decide_exit(position: Dict[str, Any],
                market_data: Dict[str, Any],
                indicators: Dict[str, Any],
                entry_regime: Dict[str, Any] | None = None,
                market_cond: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Use AI to decide whether to exit the given position.
    Returns a dict: {'decision': 'EXIT' or 'HOLD', 'reason': str}
    """
    ai_response = get_exit_decision(market_data, position, indicators, entry_regime, market_cond)

    # --- Robustly parse AI response (dict or JSON string) ---
    if isinstance(ai_response, dict):
        resp = ai_response
    elif isinstance(ai_response, str):
        try:
            resp = json.loads(ai_response)
        except json.JSONDecodeError:
            resp = None
    else:
        resp = None

    # If JSON (dict) was obtained
    if isinstance(resp, dict):
        decision_key = resp.get("action") or resp.get("decision")
        decision = decision_key.upper() if decision_key else "HOLD"
        reason   = resp.get("reason", "")
        return {"decision": decision, "reason": reason}

    # ----- Plain‑text fallback -----
    if isinstance(ai_response, str) and not isinstance(resp, dict):
        cleaned = ai_response.strip().lower()
        m = re.search(r"[a-z]+", cleaned)
        first_word = m.group(0) if m else ""
        if first_word in ("exit", "yes"):
            decision = "EXIT"
        elif first_word in ("hold", "no"):
            decision = "HOLD"
        else:
            if re.search(r"\b(exit|yes)\b", cleaned):
                decision = "EXIT"
            elif re.search(r"\b(hold|no)\b", cleaned):
                decision = "HOLD"
            else:
                decision = "HOLD"
        reason = ai_response
        return {"decision": decision, "reason": reason}

    # ----- fallback for unknown type -----
    return {"decision": "HOLD", "reason": "Unrecognized AI response"}

def process_exit(indicators, market_data, market_cond=None):
    default_pair = os.getenv("DEFAULT_PAIR", "USD_JPY")
    position = get_position_details(default_pair)
    if position is None:
        logging.info(f"No open position for {default_pair}; skip exit logic.")
        return False

    if position.get("long") and int(position["long"]["units"]) > 0:
        position_side = "long"
    elif position.get("short") and int(position["short"]["units"]) < 0:
        position_side = "short"
    else:
        logging.info("No active position found.")
        return False


    # -------- Early‑exit / break‑even logic ----------------------------
    if EARLY_EXIT_ENABLED:
        # Determine side, entry & current price
        pip_size = 0.01 if position["instrument"].endswith("_JPY") else 0.0001
        if position_side == "long":
            entry_price    = float(position["long"]["averagePrice"])
            current_price  = float(market_data["prices"][0]["bids"][0]["price"])
        else:  # short
            entry_price    = float(position["short"]["averagePrice"])
            current_price  = float(market_data["prices"][0]["asks"][0]["price"])

        profit_pips = (current_price - entry_price) / pip_size if position_side == "long" \
                      else (entry_price - current_price) / pip_size

        # Latest fast EMA & ATR
        ema_fast = indicators.get("ema_fast")
        atr_val  = indicators.get("atr")
        if hasattr(ema_fast, "iloc"):
            ema_fast = float(ema_fast.iloc[-1])
        if hasattr(atr_val, "iloc"):
            atr_val  = float(atr_val.iloc[-1])

        # Breakeven threshold
        be_buffer = BREAKEVEN_BUFFER_PIPS * pip_size

        early_exit = False
        if ema_fast is not None and atr_val is not None:
            if position_side == "long":
                if (current_price < ema_fast) and (profit_pips > 0) and \
                   (current_price <= entry_price + be_buffer):
                    early_exit = True
            else:  # short
                if (current_price > ema_fast) and (profit_pips > 0) and \
                   (current_price >= entry_price - be_buffer):
                    early_exit = True

        if early_exit:
            logging.info("Early‑exit criteria met — consulting AI before action.")
            exit_decision = decide_exit(position, market_data, indicators,
                                        entry_regime=position.get("entry_regime"),
                                        market_cond=market_cond)
            logging.info(f"AI early‑exit decision: {exit_decision['decision']} | Reason: {exit_decision['reason']}")

            if exit_decision["decision"] == "EXIT":
                order_manager.exit_trade(position)
                exit_time = datetime.utcnow().isoformat()
                units = int(position["long"]["units"]) if position_side == "long" else -int(position["short"]["units"])
                log_trade(
                    position["instrument"],
                    exit_time=exit_time,
                    entry_time=position.get("entry_time", position.get("openTime", exit_time)),
                    entry_price=entry_price,
                    units=units,
                    profit_loss=float(position["pl"]),
                    ai_reason=f"AI‑confirmed early‑exit: {exit_decision['reason']}"
                )
                return True
            else:
                logging.info("AI advised HOLD; early‑exit aborted.")
                # fall through to trailing‑stop / normal processing

    exit_decision = decide_exit(position, market_data, indicators,
                                entry_regime=position.get("entry_regime"),
                                market_cond=market_cond)
    logging.info(f"AI exit decision: {exit_decision['decision']} | Reason: {exit_decision['reason']}")

    if exit_decision["decision"] == "EXIT":
        order_manager.exit_trade(position)

        instrument = position["instrument"]

        # ポジションのunitsを取得
        if position.get("long") and int(position["long"]["units"]) > 0:
            units = int(position["long"]["units"])
            entry_price = float(position["long"]["averagePrice"])
        elif position.get("short") and int(position["short"]["units"]) < 0:
            units = -int(position["short"]["units"])  # ショートポジションは負数
            entry_price = float(position["short"]["averagePrice"])
        else:
            logging.error("No units found in position data.")
            return False

        entry_time = position.get("entry_time", position.get("openTime", datetime.utcnow().isoformat()))

        exit_price = (
            float(market_data["prices"][0]["bids"][0]["price"]) if units > 0
            else float(market_data["prices"][0]["asks"][0]["price"])
        )
        exit_time = datetime.utcnow().isoformat()

        log_trade(
            instrument,
            exit_time=exit_time,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            profit_loss=float(position["pl"]),
            ai_reason=exit_decision["reason"]
        )
        return True
    else:
        # --- Trailing‑stop logic when HOLD ---
        try:
            # Determine side and units
            if position_side == "long":
                entry_price = float(position["long"]["averagePrice"])
                current_price = float(market_data["prices"][0]["bids"][0]["price"])
                units = int(position["long"]["units"])
            else:  # short
                entry_price = float(position["short"]["averagePrice"])
                current_price = float(market_data["prices"][0]["asks"][0]["price"])
                units = -int(position["short"]["units"])

            # Calculate profit in pips
            pip_size = 0.01 if position["instrument"].endswith("_JPY") else 0.0001
            profit_pips = (current_price - entry_price) / pip_size if units > 0 else (entry_price - current_price) / pip_size

            # ---------- trailing‑stop (always ATR‑based) ---------------
            if TRAIL_ENABLED:
                # Always ATR‑based
                atr_val = indicators.get("atr")
                if atr_val is None:
                    logging.warning("ATR not found; falling back to fixed pip values.")
                    trigger_pips  = TRAIL_TRIGGER_PIPS
                    distance_pips = TRAIL_DISTANCE_PIPS
                else:
                    if hasattr(atr_val, "iloc"):
                        atr_val = atr_val.iloc[-1]
                    elif isinstance(atr_val, (list, tuple)):
                        atr_val = atr_val[-1]
                    pip_sz = 0.01 if position["instrument"].endswith("_JPY") else 0.0001
                    atr_pips      = atr_val / pip_sz
                    trigger_pips  = atr_pips * TRAIL_TRIGGER_MULTIPLIER
                    distance_pips = atr_pips * TRAIL_DISTANCE_MULTIPLIER

                if profit_pips >= trigger_pips:
                    # --- attach trailing stop to the first open trade ID ---
                    trade_ids = position.get(position_side, {}).get("tradeIDs", [])
                    if trade_ids:
                        order_manager.place_trailing_stop(
                            trade_id=trade_ids[0],
                            instrument=position["instrument"],
                            distance_pips=int(distance_pips)
                        )
                    else:
                        logging.warning("No tradeIDs found; trailing stop not placed.")
                    logging.info(
                        f"Trailing stop placed on {position['instrument']} "
                        f"({position_side}) profit={profit_pips:.1f}p, "
                        f"trigger={trigger_pips:.1f}p, distance={distance_pips:.1f}p"
                    )
        except Exception as e:
            logging.error(f"Trailing‑stop logic failed: {e}")

        return False
