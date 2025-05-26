from backend.strategy.openai_analysis import get_trade_plan
from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
from backend.orders.order_manager import OrderManager
from backend.logs.log_manager import log_trade
from datetime import datetime
from backend.utils import env_loader
import logging
import json
import uuid
# optional helper; fallback stub if module is absent
try:
    from backend.utils.oanda_client import get_pending_entry_order  # type: ignore
except ModuleNotFoundError:
    def get_pending_entry_order(instrument: str):
        return None

# env_loader automatically loads default env files at import time

order_manager = OrderManager()

# In‑memory cache: entry_uuid -> {"instrument": str, "order_id": str, "ts": int}
_pending_limits: dict[str, dict] = {}

def pullback_limit(side: str, price: float, offset_pips: float) -> float:
    """Return limit price offset by given pips in the direction of a pullback."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    return price - offset_pips * pip_size if side == "long" else price + offset_pips * pip_size


def calculate_pullback_offset(indicators: dict, market_cond: dict | None) -> float:
    """Return dynamic pullback offset in pips.

    The base value comes from ``PULLBACK_LIMIT_OFFSET_PIPS`` and is adjusted
    according to the latest ATR value and trend strength (ADX).
    """
    offset = float(env_loader.get_env("PULLBACK_LIMIT_OFFSET_PIPS", "2"))
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))

        atr_series = indicators.get("atr")
        if atr_series is not None and len(atr_series):
            atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            atr_pips = float(atr_val) / pip_size
            ratio = float(env_loader.get_env("PULLBACK_ATR_RATIO", "0.5"))
            offset = offset + atr_pips * ratio

        adx_series = indicators.get("adx")
        if (
            market_cond
            and market_cond.get("market_condition") == "trend"
            and adx_series is not None
            and len(adx_series)
        ):
            adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
            if float(adx_val) >= 30:
                offset *= 1.5
            elif float(adx_val) < 20:
                offset *= 0.7
    except Exception as exc:
        logging.debug(f"[calculate_pullback_offset] failed: {exc}")

    return offset


def process_entry(
    indicators,
    candles,
    market_data,
    market_cond: dict | None = None,
    strategy_params=None,
    *,
    higher_tf: dict | None = None,
    patterns: list[str] | None = None,
    pattern_names: dict[str, str | None] | None = None,
):
    """
    Ask OpenAI whether to enter a trade.

    Args:
        indicators: dict of calculated indicators
        candles   : recent candle list (passed through, not used here—kept for API consistency)
        market_data: latest tick data (dict from OANDA)
        market_cond: output of get_market_condition()  e.g. {"market_condition":"trend","trend_direction":"long"}
        strategy_params: optional dict to pass extra parameters / overrides

    Returns:
        True if an entry was placed, False otherwise.
    """
    # If the caller did not pass a dict (JobRunner passes candles), fall back to an empty dict
    if not isinstance(strategy_params, dict):
        strategy_params = {}

    # ------------------------------------------------------------
    #  Step 1: call unified LLM helper
    # ------------------------------------------------------------
    candles_dict = {"M5": candles}
    indicators_multi = {"M5": indicators}
    plan = get_trade_plan(
        market_data,
        indicators_multi,
        candles_dict,
        patterns=patterns,
        detected_patterns=pattern_names,
    )

    # Raw JSON for audit log
    ai_raw = json.dumps(plan, ensure_ascii=False)
    logging.info(f"AI trade plan raw: {ai_raw}")

    entry_info = plan.get("entry", {})
    risk_info  = plan.get("risk", {})

    side = entry_info.get("side", "no").lower()
    if side not in ("long", "short"):
        logging.info("AI says no trade entry → early exit")
        return False

    mode = entry_info.get("mode", "market")
    limit_price = entry_info.get("limit_price")
    valid_sec = int(entry_info.get("valid_for_sec", env_loader.get_env("MAX_LIMIT_AGE_SEC", "180")))

    # --- dynamic pullback threshold ---------------------------------
    pullback_needed = None
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        atr_series = indicators.get("atr")
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        atr_val = atr_series.iloc[-1] if atr_series is not None else None
        if atr_val is not None:
            atr_val = float(atr_val)
        bw_val = None
        if bb_upper is not None and bb_lower is not None:
            bw_val = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
        atr_pips = atr_val / pip_size if atr_val is not None else 0.0
        bw_pips = bw_val / pip_size if bw_val is not None else 0.0
        class _OneVal:
            def __init__(self, val):
                class _IL:
                    def __getitem__(self, idx):
                        return val
                self.iloc = _IL()

        noise_series = _OneVal(max(atr_pips, bw_pips))
        highs = []
        lows = []
        for c in candles[-20:]:
            if 'mid' in c:
                highs.append(float(c['mid']['h']))
                lows.append(float(c['mid']['l']))
            else:
                highs.append(float(c.get('h')))
                lows.append(float(c.get('l')))
        recent_high = max(highs) if highs else 0.0
        recent_low = min(lows) if lows else 0.0
        pullback_needed = calculate_dynamic_pullback({**indicators, 'noise': noise_series}, recent_high, recent_low)
    except Exception:
        pass

    if isinstance(market_data, dict):
        instrument = market_data["prices"][0]["instrument"]
        bid = float(market_data["prices"][0]["bids"][0]["price"])
        ask = float(market_data["prices"][0]["asks"][0]["price"])
    else:
        instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
        bid = ask = None

    if mode == "market":
        price_ref = bid if side == "long" else ask
        offset = 0.0
        if higher_tf and price_ref is not None:
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            sup_pips = float(env_loader.get_env("PIVOT_SUPPRESSION_PIPS", "15"))
            base_pullback = float(env_loader.get_env("PULLBACK_PIPS", "3"))
            pullback = pullback_needed if pullback_needed is not None else base_pullback
            tfs = [
                tf.strip().upper()
                for tf in env_loader.get_env("PIVOT_SUPPRESSION_TFS", "D").split(",")
                if tf.strip()
            ]
            for tf in tfs:
                pivot = higher_tf.get(f"pivot_{tf.lower()}")
                if pivot is None:
                    continue
                if abs((price_ref - pivot) / pip_size) <= sup_pips:
                    offset = pullback
                    break
        if offset == 0.0:
            offset = calculate_pullback_offset(indicators, market_cond)
        if pullback_needed is not None:
            offset = max(offset, pullback_needed)
        if offset and price_ref is not None:
            limit_price = pullback_limit(side, price_ref, offset)

    # ------------------------------------------------------------
    #  Detect narrow-range market (Bollinger band width < threshold)
    # ------------------------------------------------------------
    narrow_range = False
    try:
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
            bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
            narrow_range = bw_pips < bw_thresh
    except Exception as exc:
        logging.debug(f"[process_entry] narrow-range detection failed: {exc}")

    # ------------------------------------------------------------
    #  Range market handling: switch to LIMIT if near BB center
    # ------------------------------------------------------------
    try:
        if (
            (market_cond and market_cond.get("market_condition") == "range")
            or narrow_range
        ) and bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            price_ref = bid if side == "long" else ask
            if price_ref is not None:
                center = (bb_upper.iloc[-1] + bb_lower.iloc[-1]) / 2
                distance_pips = abs(price_ref - center) / pip_size
                offset_threshold = float(
                    env_loader.get_env("RANGE_ENTRY_OFFSET_PIPS", "3")
                )
                if distance_pips <= offset_threshold:
                    target = bb_lower.iloc[-1] if side == "long" else bb_upper.iloc[-1]
                    offset_pips = abs(price_ref - target) / pip_size
                    limit_price = pullback_limit(side, price_ref, offset_pips)
                    mode = "limit"
    except Exception as exc:
        logging.debug(f"[process_entry] range-limit conversion failed: {exc}")

    if mode == "wait":
        logging.info("AI suggests WAIT – re‑evaluate next loop.")
        return False

    tp_pips = risk_info.get("tp_pips")
    sl_pips = risk_info.get("sl_pips")
    fallback_tp = None

    min_sl = float(env_loader.get_env("MIN_SL_PIPS", "0"))
    fallback_sl = None
    try:
        atr_series = indicators.get("atr")
        if atr_series is not None and len(atr_series):
            if hasattr(atr_series, "iloc"):
                atr_val = float(atr_series.iloc[-1])
            else:
                atr_val = float(atr_series[-1])
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            mult = float(env_loader.get_env("ATR_SL_MULTIPLIER", "2.0"))
            fallback_sl = atr_val / pip_size * mult
            tp_ratio = float(env_loader.get_env("SHORT_TP_ATR_RATIO", "0.6"))
            fallback_tp = atr_val / pip_size * tp_ratio
        price_ref = bid if side == "long" else ask
        pivot_key = "pivot_r1" if side == "long" else "pivot_s1"
        pivot_val = indicators.get(pivot_key)
        if pivot_val is not None and price_ref is not None:
            dist = abs(pivot_val - price_ref) / pip_size
            if fallback_tp is None or dist < fallback_tp:
                fallback_tp = dist
        n_target = indicators.get("n_wave_target")
        if n_target is not None and price_ref is not None:
            dist = abs(n_target - price_ref) / pip_size
            if fallback_tp is None or dist < fallback_tp:
                fallback_tp = dist
    except Exception as exc:
        logging.debug(f"[process_entry] ATR-based SL calc failed: {exc}")

    if tp_pips is None:
        tp_pips = fallback_tp if fallback_tp is not None else float(env_loader.get_env("INIT_TP_PIPS", "30"))
    else:
        try:
            tp_pips = float(tp_pips)
        except Exception:
            tp_pips = float(env_loader.get_env("INIT_TP_PIPS", "30"))

    if sl_pips is None:
        sl_pips = fallback_sl if fallback_sl is not None else float(env_loader.get_env("INIT_SL_PIPS", "20"))
    else:
        try:
            sl_pips = float(sl_pips)
        except Exception:
            sl_pips = float(env_loader.get_env("INIT_SL_PIPS", "20"))

    if fallback_sl is not None:
        sl_pips = max(sl_pips, fallback_sl)
    if sl_pips < min_sl:
        sl_pips = min_sl
    logging.info(f"AI Entry {side} – tp={tp_pips}  sl={sl_pips} (pips)")

    if mode == "limit":
        if limit_price is None:
            logging.warning("LIMIT mode but no limit_price → skip entry.")
            return False

        # Check if a similar pending order already exists
        existing = get_pending_entry_order(instrument)
        if existing:
            logging.info("Pending LIMIT order already exists – skip new limit placement.")
            return False

        entry_uuid = str(uuid.uuid4())[:8]
        params_limit = {
            "instrument": instrument,
            "side": side,
            "tp_pips": tp_pips,
            "sl_pips": sl_pips,
            "mode": "limit",
            "limit_price": limit_price,
            "entry_uuid": entry_uuid,
            "valid_for_sec": valid_sec,
            "ai_response": ai_raw,
            "market_cond": market_cond,
        }
        result = order_manager.enter_trade(
            side=side,
            lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
            market_data=market_data,
            strategy_params=params_limit,
            force_limit_only=False,
        )
        if result:
            _pending_limits[entry_uuid] = {
                "instrument": instrument,
                "order_id": result.get("order_id"),
                "ts": int(datetime.utcnow().timestamp()),
                "limit_price": limit_price,
                "side": side,
                "retry_count": 0,
            }
        return bool(result)
    else:
        # --- MARKET order path ---
        params = {
            **strategy_params,
            "instrument": instrument,
            "side": side,
            "tp_pips": tp_pips,
            "sl_pips": sl_pips,
            "mode": "market",
            "limit_price": limit_price,
            "ai_response": ai_raw,
            "market_cond": market_cond,
        }

    trade_result = order_manager.enter_trade(
        side=side,
        lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
        market_data=market_data,
        strategy_params=params,
        force_limit_only=False
    )

    if trade_result and mode == "market":
        instrument = params["instrument"]
        lot_size = float(env_loader.get_env("TRADE_LOT_SIZE", "1.0"))
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_price = float(market_data['prices'][0]['bids'][0]['price'])
        entry_time = datetime.utcnow().isoformat()
        log_trade(
            instrument,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            ai_reason=ai_raw,
            ai_response=ai_raw
        )

    return True
