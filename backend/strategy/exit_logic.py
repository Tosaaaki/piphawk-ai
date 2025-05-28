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
# 低ボラ停滞時の早期利確設定
STAGNANT_EXIT_SEC   = int(os.getenv("STAGNANT_EXIT_SEC", "0"))
STAGNANT_ATR_PIPS   = float(os.getenv("STAGNANT_ATR_PIPS", "0"))

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


def decide_exit(
    position: Dict[str, Any],
    market_data: Dict[str, Any],
    indicators: Dict[str, Any],
    entry_regime: Dict[str, Any] | None = None,
    market_cond: Dict[str, Any] | None = None,
    *,
    higher_tf: Dict[str, Any] | None = None,
    indicators_m1: Dict[str, Any] | None = None,
    patterns: list[str] | None = None,
    pattern_names: Dict[str, str | None] | None = None,
) -> Dict[str, Any]:
    """
    Use AI to decide whether to exit the given position.
    Returns a dict: {'decision': 'EXIT' or 'HOLD', 'reason': str}
    """
    # --- Compute time since entry and pips moved for additional context ---
    context_data = dict(market_data)
    secs_since_entry = None
    pips_from_entry = 0.0
    try:
        entry_time_str = position.get("entry_time") or position.get("openTime")
        if entry_time_str:
            entry_dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
            secs_since_entry = (datetime.utcnow() - entry_dt).total_seconds()
    except Exception:
        secs_since_entry = None

    try:
        pip_size = 0.01 if position["instrument"].endswith("_JPY") else 0.0001
        if position.get("long") and int(position["long"].get("units", 0)) > 0:
            entry_price = float(position["long"]["averagePrice"])
            current_price = float(market_data["prices"][0]["bids"][0]["price"])
            pips_from_entry = (current_price - entry_price) / pip_size
        elif position.get("short") and int(position["short"].get("units", 0)) < 0:
            entry_price = float(position["short"]["averagePrice"])
            current_price = float(market_data["prices"][0]["asks"][0]["price"])
            pips_from_entry = (entry_price - current_price) / pip_size
    except Exception:
        pips_from_entry = 0.0

    context_data["secs_since_entry"] = secs_since_entry
    context_data["pips_from_entry"] = pips_from_entry

    ai_response = get_exit_decision(
        context_data,
        position,
        indicators,
        entry_regime,
        market_cond,
        higher_tf=higher_tf,
        indicators_m1=indicators_m1,
        patterns=patterns,
        detected_patterns=pattern_names,
    )
    raw = ai_response if isinstance(ai_response, str) else json.dumps(ai_response)

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
        return {"decision": decision, "reason": reason, "raw": raw}

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
        return {"decision": decision, "reason": reason, "raw": raw}

    # ----- fallback for unknown type -----
    return {"decision": "HOLD", "reason": "Unrecognized AI response", "raw": raw}

def process_exit(
    indicators,
    market_data,
    market_cond=None,
    higher_tf=None,
    indicators_m1=None,
    patterns=None,
    pattern_names=None,
):
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

    # -------- Market regime shift check --------------------------------
    entry_regime = None
    try:
        er_raw = position.get("entry_regime")
        if er_raw:
            entry_regime = json.loads(er_raw)
    except Exception:
        entry_regime = None

    regime_action = None
    if entry_regime and isinstance(market_cond, dict):
        curr_cond = market_cond.get("market_condition")
        curr_dir = market_cond.get("trend_direction")
        prev_cond = entry_regime.get("market_condition")
        prev_dir = entry_regime.get("trend_direction")
        if curr_cond != prev_cond or curr_dir != prev_dir:
            favorable = (
                curr_cond == "trend"
                and curr_dir is not None
                and ((curr_dir == "long" and position_side == "long") or (curr_dir == "short" and position_side == "short"))
            )
            regime_action = "HOLD" if favorable else "EXIT"

    if regime_action == "EXIT":
        logging.info("Regime shift unfavorable → closing position early.")
        order_manager.exit_trade(position)
        exit_time = datetime.utcnow().isoformat()
        units = int(position["long"]["units"]) if position_side == "long" else -int(position["short"]["units"])
        log_trade(
            position["instrument"],
            exit_time=exit_time,
            entry_time=position.get("entry_time", exit_time),
            entry_price=float(position[position_side]["averagePrice"]),
            units=units,
            profit_loss=float(position["pl"]),
            ai_reason="regime shift exit",
        )
        return True
    elif regime_action == "HOLD":
        logging.info("Regime shift favors current position → HOLD")


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

        # 低ボラで利益が伸びない場合の撤退チェック
        if not early_exit and STAGNANT_EXIT_SEC > 0 and STAGNANT_ATR_PIPS > 0:
            if atr_val is not None and (atr_val / pip_size) <= STAGNANT_ATR_PIPS:
                entry_ts = position.get("entry_time") or position.get("openTime")
                if entry_ts:
                    try:
                        et = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                        held_sec = (datetime.utcnow() - et).total_seconds()
                        if held_sec >= STAGNANT_EXIT_SEC and profit_pips > 0:
                            early_exit = True
                    except Exception:
                        pass

        if early_exit:
            logging.info("Early‑exit criteria met — consulting AI before action.")
            exit_decision = decide_exit(
                position,
                market_data,
                indicators,
                entry_regime=position.get("entry_regime"),
                market_cond=market_cond,
                higher_tf=higher_tf,
                indicators_m1=indicators_m1,
                patterns=patterns,
                pattern_names=pattern_names,
            )
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
                    ai_reason=f"AI‑confirmed early‑exit: {exit_decision['reason']}",
                    ai_response=exit_decision.get("raw")
                )
                return True
            else:
                logging.info("AI advised HOLD; early‑exit aborted.")
                # fall through to trailing‑stop / normal processing

    exit_decision = decide_exit(
        position,
        market_data,
        indicators,
        entry_regime=position.get("entry_regime"),
        market_cond=market_cond,
        higher_tf=higher_tf,
        indicators_m1=indicators_m1,
        patterns=patterns,
        pattern_names=pattern_names,
    )
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
            ai_reason=exit_decision["reason"],
            ai_response=exit_decision.get("raw")
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

            # ---------- partial close check -----------------------------
            partial_thresh = float(os.getenv("PARTIAL_CLOSE_PIPS", "0"))
            partial_ratio = float(os.getenv("PARTIAL_CLOSE_RATIO", "0"))
            if partial_thresh > 0 and partial_ratio > 0 and profit_pips >= partial_thresh:
                trade_ids = position.get(position_side, {}).get("tradeIDs", [])
                if trade_ids:
                    close_units = int(abs(units) * partial_ratio)
                    if close_units > 0:
                        close_units = close_units if units > 0 else -close_units
                        order_manager.close_partial(trade_ids[0], close_units)
                        log_trade(
                            position["instrument"],
                            entry_time=position.get("entry_time", position.get("openTime", datetime.utcnow().isoformat())),
                            entry_price=entry_price,
                            units=close_units,
                            ai_reason="partial close",
                            exit_time=datetime.utcnow().isoformat(),
                            exit_price=current_price,
                        )
                        units -= close_units

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

                logging.info(
                    f"Trailing stop check: profit={profit_pips:.1f}p "
                    f"trigger={trigger_pips:.1f}p"
                )

                # 利益が十分にある場合のみトレーリングストップを検討する
                if profit_pips >= trigger_pips:
                    # 利益より距離が大きい場合は発注しない
                    if profit_pips - distance_pips <= 0:
                        logging.warning(
                            "Trailing-stop skipped: distance exceeds current profit"
                        )
                    else:
                        # --- attach trailing stop to the first open trade ID ---
                        trade_ids = position.get(position_side, {}).get("tradeIDs", [])
                        if trade_ids:
                            order_manager.place_trailing_stop(
                                trade_id=trade_ids[0],
                                instrument=position["instrument"],
                                distance_pips=int(distance_pips)
                            )
                        else:
                            logging.warning("Trailing-stop placement skipped: missing trade IDs")
                        logging.info(
                            f"Trailing stop placed on {position['instrument']} "
                            f"({position_side}) profit={profit_pips:.1f}p, "
                            f"trigger={trigger_pips:.1f}p, distance={distance_pips:.1f}p"
                        )
                else:
                    logging.debug(
                        f"Trailing stop not triggered: profit={profit_pips:.1f}p < "
                        f"trigger={trigger_pips:.1f}p"
                    )
        except Exception as e:
            logging.error(f"Trailing‑stop logic failed: {e}")

        return False
