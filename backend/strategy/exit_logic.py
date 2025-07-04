import importlib
from typing import Any, Dict

openai_analysis = importlib.import_module("backend.strategy.openai_analysis")
EXIT_BIAS_FACTOR = getattr(openai_analysis, "EXIT_BIAS_FACTOR", 1.0)
import logging
from datetime import datetime, timezone

from backend.logs.exit_logger import append_exit_log
from backend.logs.trade_logger import ExitReason, log_trade
from backend.orders.order_manager import OrderManager
from backend.utils import env_loader, trade_age_seconds

# Trailing‑stop configuration
TRAIL_TRIGGER_PIPS = float(

    env_loader.get_env("TRAIL_TRIGGER_PIPS", "10")

)  # profit threshold to arm trailing stop
TRAIL_DISTANCE_PIPS = float(
    env_loader.get_env("TRAIL_DISTANCE_PIPS", "6")
)  # distance of the trailing stop itself
# Toggle for enabling/disabling trailing‑stop logic
TRAIL_ENABLED = env_loader.get_env("TRAIL_ENABLED", "true").lower() == "true"

# --- Early‑exit & breakeven settings ------------------------------------
EARLY_EXIT_ENABLED = env_loader.get_env("EARLY_EXIT_ENABLED", "true").lower() == "true"
BREAKEVEN_BUFFER_PIPS = float(
    env_loader.get_env("BREAKEVEN_BUFFER_PIPS", "2")
)  # pips offset from BE
# 低ボラ停滞時の早期利確設定
STAGNANT_EXIT_SEC = int(env_loader.get_env("STAGNANT_EXIT_SEC", "0"))
STAGNANT_ATR_PIPS = float(env_loader.get_env("STAGNANT_ATR_PIPS", "0"))

# 逆行判定のための閾値設定
REVERSAL_EXIT_ATR_MULT = float(env_loader.get_env("REVERSAL_EXIT_ATR_MULT", "1.0"))
REVERSAL_EXIT_ADX_MIN = float(env_loader.get_env("REVERSAL_EXIT_ADX_MIN", "25"))

# ATRが高くADXが低いときの早期撤退判定に使う閾値
HIGH_ATR_PIPS = float(env_loader.get_env("HIGH_ATR_PIPS", "10"))
LOW_ADX_THRESH = float(env_loader.get_env("LOW_ADX_THRESH", "20"))

# polarity-based exit threshold
POLARITY_EXIT_THRESHOLD = float(env_loader.get_env("POLARITY_EXIT_THRESHOLD", "0.4"))

# DIクロスによる早期決済を行う際のADX下限
DI_CROSS_EXIT_ADX_MIN = float(
    env_loader.get_env("DI_CROSS_EXIT_ADX_MIN", "25")
)

# 早期撤退を行う際の最低利益幅（pips）
MIN_EARLY_EXIT_PROFIT_PIPS = float(
    env_loader.get_env("MIN_EARLY_EXIT_PROFIT_PIPS", "5")
)

# Dynamic ATR‑based trailing‑stop (always enabled)
TRAIL_TRIGGER_MULTIPLIER = float(env_loader.get_env("TRAIL_TRIGGER_MULTIPLIER", "1.2"))
TRAIL_DISTANCE_MULTIPLIER = float(env_loader.get_env("TRAIL_DISTANCE_MULTIPLIER", "1.0"))
# カレンダーイベント時の追加距離倍率
CALENDAR_VOL_THRESHOLD = int(env_loader.get_env("CALENDAR_VOL_THRESHOLD", "3"))
CALENDAR_TRAIL_MULTIPLIER = float(env_loader.get_env("CALENDAR_TRAIL_MULTIPLIER", "1.5"))
import json

from backend.orders.position_manager import get_position_details

order_manager = OrderManager()


def generate_position_condition_prompt(
    position: Dict[str, Any], market_data: Dict[str, Any], indicators: Dict[str, Any]
) -> str:
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
            secs_since_entry = (datetime.now(timezone.utc) - entry_dt).total_seconds()
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


    ai_context = {
        **context_data,
        "position": position,
        "indicators": indicators,
        "entry_regime": entry_regime,
        "market_cond": market_cond,
        "entry_vol_pips": None if not entry_regime else entry_regime.get("vol"),
        "entry_stance": None if not entry_regime else entry_regime.get("stance"),
    }
    oa = importlib.import_module("backend.strategy.openai_analysis")
    exit_eval = getattr(oa, "evaluate_exit", None)
    if exit_eval:
        decision_obj = exit_eval(ai_context, bias_factor=getattr(oa, "EXIT_BIAS_FACTOR", EXIT_BIAS_FACTOR))
        ai_response = decision_obj.as_dict()
    else:
        ai_response = {"action": "HOLD", "reason": "no evaluator"}
    raw = json.dumps(ai_response)

    decision_key = ai_response.get("action") or ai_response.get("decision")
    decision = decision_key.upper() if decision_key else "HOLD"
    reason = ai_response.get("reason", "")
    return {"decision": decision, "reason": reason, "raw": raw}



def process_exit(
    indicators,
    market_data,
    market_cond=None,
    higher_tf=None,
    indicators_m1=None,
    patterns=None,
    pattern_names=None,
):
    default_pair = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
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

    # --- Check minimum hold time ---------------------------------------
    secs_since_entry = trade_age_seconds(position)
    min_hold = int(env_loader.get_env("MIN_HOLD_SECONDS", "0"))
    if secs_since_entry is not None and secs_since_entry < min_hold:
        logging.info(
            f"Held {secs_since_entry:.1f}s < MIN_HOLD_SECONDS {min_hold} → skip exit logic."
        )
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
                and (
                    (curr_dir == "long" and position_side == "long")
                    or (curr_dir == "short" and position_side == "short")
                )
            )
            regime_action = "HOLD" if favorable else "EXIT"

    if regime_action == "EXIT":
        logging.info("Regime shift unfavorable → closing position early.")
        order_manager.exit_trade(position)
        exit_time = datetime.now(timezone.utc).isoformat()
        units = (
            int(position["long"]["units"])
            if position_side == "long"
            else -int(position["short"]["units"])
        )
        log_trade(
            instrument=position["instrument"],
            exit_time=exit_time,
            entry_time=position.get("entry_time", exit_time),
            entry_price=float(position[position_side]["averagePrice"]),
            units=units,
            profit_loss=float(position.get("pl_corrected", position.get("pl", 0))),
            ai_reason="regime shift exit",
            exit_reason=ExitReason.AI,
            is_manual=False,
        )
        return True
    elif regime_action == "HOLD":
        logging.info("Regime shift favors current position → HOLD")

    # -------- Early‑exit / break‑even logic ----------------------------
    if EARLY_EXIT_ENABLED:
        # Determine side, entry & current price
        pip_size = 0.01 if position["instrument"].endswith("_JPY") else 0.0001
        if position_side == "long":
            entry_price = float(position["long"]["averagePrice"])
            current_price = float(market_data["prices"][0]["bids"][0]["price"])
        else:  # short
            entry_price = float(position["short"]["averagePrice"])
            current_price = float(market_data["prices"][0]["asks"][0]["price"])

        profit_pips = (
            (current_price - entry_price) / pip_size
            if position_side == "long"
            else (entry_price - current_price) / pip_size
        )

        # Latest fast EMA & ATR
        ema_fast = indicators.get("ema_fast")
        atr_val = indicators.get("atr")
        if hasattr(ema_fast, "iloc"):
            ema_fast = float(ema_fast.iloc[-1])
        if hasattr(atr_val, "iloc"):
            atr_val = float(atr_val.iloc[-1])

        # Breakeven threshold
        be_buffer = BREAKEVEN_BUFFER_PIPS * pip_size

        early_exit = False
        if (
            ema_fast is not None
            and atr_val is not None
            and profit_pips >= MIN_EARLY_EXIT_PROFIT_PIPS
        ):
            if position_side == "long":
                if (
                    current_price < ema_fast
                    and current_price <= entry_price + be_buffer
                ):
                    early_exit = True
            else:  # short
                if (
                    current_price > ema_fast
                    and current_price >= entry_price - be_buffer
                ):
                    early_exit = True

        # ボリンジャーバンドを用いた逆行判定
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        adx_val = indicators.get("adx")
        if hasattr(bb_upper, "iloc"):
            bb_upper = float(bb_upper.iloc[-1])
        if hasattr(bb_lower, "iloc"):
            bb_lower = float(bb_lower.iloc[-1])
        if hasattr(adx_val, "iloc"):
            adx_val = float(adx_val.iloc[-1])

        # ATR が非常に大きく ADX が低い場合は早期撤退を検討
        if (
            atr_val is not None
            and adx_val is not None
            and (atr_val / pip_size) >= HIGH_ATR_PIPS
            and adx_val < LOW_ADX_THRESH
        ):
            early_exit = True

        if (
            atr_val is not None
            and bb_upper is not None
            and bb_lower is not None
            and adx_val is not None
        ):
            atr_pips = atr_val / pip_size
            if position_side == "long" and current_price < bb_lower:
                diff_pips = (bb_lower - current_price) / pip_size
                if (
                    diff_pips >= atr_pips * REVERSAL_EXIT_ATR_MULT
                    and adx_val >= REVERSAL_EXIT_ADX_MIN
                ):
                    early_exit = True
            elif position_side == "short" and current_price > bb_upper:
                diff_pips = (current_price - bb_upper) / pip_size
                if (
                    diff_pips >= atr_pips * REVERSAL_EXIT_ATR_MULT
                    and adx_val >= REVERSAL_EXIT_ADX_MIN
                ):
                    early_exit = True

        # 低ボラで利益が伸びない場合の撤退チェック
        if not early_exit and STAGNANT_EXIT_SEC > 0 and STAGNANT_ATR_PIPS > 0:
            if atr_val is not None and (atr_val / pip_size) <= STAGNANT_ATR_PIPS:
                entry_ts = position.get("entry_time") or position.get("openTime")
                if entry_ts:
                    try:
                        et = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                        held_sec = (datetime.now(timezone.utc) - et).total_seconds()
                        if held_sec >= STAGNANT_EXIT_SEC and profit_pips > 0:
                            early_exit = True
                    except Exception:
                        pass

        # polarity check
        if not early_exit:
            polarity = indicators.get("polarity")
            if hasattr(polarity, "iloc"):
                polarity = float(polarity.iloc[-1])
            if polarity is not None:
                if (
                    (position_side == "long" and polarity <= -POLARITY_EXIT_THRESHOLD)
                    or (position_side == "short" and polarity >= POLARITY_EXIT_THRESHOLD)
                ):
                    early_exit = True

        # DIクロス判定
        if not early_exit:
            di_plus = indicators.get("plus_di")
            di_minus = indicators.get("minus_di")
            adx_val = indicators.get("adx")
            if hasattr(adx_val, "iloc"):
                adx_val = float(adx_val.iloc[-1])
            elif isinstance(adx_val, (list, tuple)):
                adx_val = float(adx_val[-1])
            try:
                if (
                    di_plus is not None
                    and di_minus is not None
                    and len(di_plus) >= 2
                    and len(di_minus) >= 2
                ):
                    p_prev = di_plus.iloc[-2] if hasattr(di_plus, "iloc") else di_plus[-2]
                    p_cur = di_plus.iloc[-1] if hasattr(di_plus, "iloc") else di_plus[-1]
                    m_prev = di_minus.iloc[-2] if hasattr(di_minus, "iloc") else di_minus[-2]
                    m_cur = di_minus.iloc[-1] if hasattr(di_minus, "iloc") else di_minus[-1]
                    crossed = False
                    if position_side == "long" and p_prev > m_prev and p_cur < m_cur:
                        crossed = True
                    elif position_side == "short" and m_prev > p_prev and m_cur < p_cur:
                        crossed = True
                    if crossed and adx_val is not None and adx_val >= DI_CROSS_EXIT_ADX_MIN:
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
            logging.info(
                f"AI early‑exit decision: {exit_decision['decision']} | Reason: {exit_decision['reason']}"
            )

            if exit_decision["decision"] == "EXIT":
                order_manager.exit_trade(position)
                exit_time = datetime.now(timezone.utc).isoformat()
                units = (
                    int(position["long"]["units"])
                    if position_side == "long"
                    else -int(position["short"]["units"])
                )
                log_trade(
                    instrument=position["instrument"],
                    exit_time=exit_time,
                    entry_time=position.get(
                        "entry_time", position.get("openTime", exit_time)
                    ),
                    entry_price=entry_price,
                    units=units,
                    profit_loss=float(position.get("pl_corrected", position.get("pl", 0))),
                    ai_reason=f"AI‑confirmed early‑exit: {exit_decision['reason']}",
                    ai_response=exit_decision.get("raw"),
                    exit_reason=ExitReason.AI,
                    is_manual=False,
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
    logging.info(
        f"AI exit decision: {exit_decision['decision']} | Reason: {exit_decision['reason']}"
    )

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

        entry_time = position.get(
            "entry_time", position.get("openTime", datetime.now(timezone.utc).isoformat())
        )

        exit_price = (
            float(market_data["prices"][0]["bids"][0]["price"])
            if units > 0
            else float(market_data["prices"][0]["asks"][0]["price"])
        )
        exit_time = datetime.now(timezone.utc).isoformat()

        log_trade(
            instrument=instrument,
            exit_time=exit_time,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            profit_loss=float(position.get("pl_corrected", position.get("pl", 0))),
            ai_reason=exit_decision["reason"],
            ai_response=exit_decision.get("raw"),
            exit_reason=ExitReason.AI,
            is_manual=False,
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
            profit_pips = (
                (current_price - entry_price) / pip_size
                if units > 0
                else (entry_price - current_price) / pip_size
            )


            # ---------- partial close check -----------------------------
            partial_thresh = float(env_loader.get_env("PARTIAL_CLOSE_PIPS", "0"))
            partial_ratio = float(env_loader.get_env("PARTIAL_CLOSE_RATIO", "0"))
            if partial_thresh > 0 and partial_ratio > 0 and profit_pips >= partial_thresh:
                trade_ids = position.get(position_side, {}).get("tradeIDs", [])
                if trade_ids:
                    close_units = int(abs(units) * partial_ratio)
                    if close_units > 0:
                        close_units = close_units if units > 0 else -close_units
                        order_manager.close_partial(trade_ids[0], close_units)
                        log_trade(
                            instrument=position["instrument"],
                            entry_time=position.get("entry_time", position.get("openTime", datetime.now(timezone.utc).isoformat())),
                            entry_price=entry_price,
                            units=close_units,
                            ai_reason="partial close",
                            exit_time=datetime.now(timezone.utc).isoformat(),
                            exit_price=current_price,
                            exit_reason=ExitReason.RISK,
                            is_manual=False,
                        )
                        units -= close_units

            # ---------- trailing‑stop (always ATR‑based) ---------------
            if TRAIL_ENABLED:
                # Always ATR‑based
                atr_val = indicators.get("atr")
                if atr_val is None:
                    logging.warning("ATR not found; falling back to fixed pip values.")
                    trigger_pips = TRAIL_TRIGGER_PIPS
                    distance_pips = TRAIL_DISTANCE_PIPS
                else:
                    if hasattr(atr_val, "iloc"):
                        atr_val = atr_val.iloc[-1]
                    elif isinstance(atr_val, (list, tuple)):
                        atr_val = atr_val[-1]
                    pip_sz = 0.01 if position["instrument"].endswith("_JPY") else 0.0001

                    atr_pips = atr_val / pip_sz
                    trigger_pips = atr_pips * TRAIL_TRIGGER_MULTIPLIER

                    distance_pips = atr_pips * TRAIL_DISTANCE_MULTIPLIER
                    # 高ボラ指標発表時は距離を広げる
                    atr_pips = atr_val / pip_sz
                    trigger_pips = max(
                        atr_pips * TRAIL_TRIGGER_MULTIPLIER,
                        TRAIL_TRIGGER_PIPS,
                    )
                    distance_pips = max(
                        atr_pips * TRAIL_DISTANCE_MULTIPLIER,
                        TRAIL_DISTANCE_PIPS,
                    )
                    if int(env_loader.get_env("CALENDAR_VOLATILITY_LEVEL", "0")) > CALENDAR_VOL_THRESHOLD:
                        distance_pips *= CALENDAR_TRAIL_MULTIPLIER


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
                            current_distance = None
                            if hasattr(order_manager, "get_current_trailing_distance"):
                                current_distance = order_manager.get_current_trailing_distance(
                                    trade_ids[0], position["instrument"]
                                )
                            if current_distance is not None and int(current_distance) == int(distance_pips):
                                logging.debug(
                                    "Trailing stop unchanged: %dp", int(distance_pips)
                                )
                            else:
                                order_manager.place_trailing_stop(
                                    trade_id=trade_ids[0],
                                    instrument=position["instrument"],
                                    distance_pips=int(distance_pips),
                                )
                            try:
                                bid = float(
                                    market_data["prices"][0]["bids"][0]["price"]
                                )
                                ask = float(
                                    market_data["prices"][0]["asks"][0]["price"]
                                )
                                pip_sz = (
                                    0.01
                                    if position["instrument"].endswith("_JPY")
                                    else 0.0001
                                )
                                spread = (ask - bid) / pip_sz
                                atr_current = indicators.get("atr")
                                if hasattr(atr_current, "iloc"):
                                    atr_current = float(atr_current.iloc[-1])
                                elif isinstance(atr_current, (list, tuple)):
                                    atr_current = float(atr_current[-1])
                                atr_pips = (
                                    atr_current / pip_sz
                                    if atr_current is not None
                                    else None
                                )
                                append_exit_log(
                                    {
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "instrument": position["instrument"],
                                        "price": current_price,
                                        "spread": spread,
                                        "atr": atr_pips,
                                    }
                                )
                            except Exception as exc:
                                logging.error(f"exit_log write failed: {exc}")
                        else:
                            logging.warning(
                                "Trailing-stop placement skipped: missing trade IDs"
                            )
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
