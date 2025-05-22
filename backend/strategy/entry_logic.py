from backend.strategy.openai_analysis import get_trade_plan
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
            pullback = float(env_loader.get_env("PULLBACK_PIPS", "3"))
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

    if mode == "wait":
        logging.info("AI suggests WAIT – re‑evaluate next loop.")
        return False

    tp_pips = risk_info.get("tp_pips")
    sl_pips = risk_info.get("sl_pips")
    if sl_pips is None:
        try:
            atr_series = indicators.get("atr")
            if atr_series is not None and len(atr_series):
                if hasattr(atr_series, "iloc"):
                    atr_val = float(atr_series.iloc[-1])
                else:
                    atr_val = float(atr_series[-1])
                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                mult = float(env_loader.get_env("ATR_SL_MULTIPLIER", "2.0"))
                sl_pips = atr_val / pip_size * mult
            else:
                raise ValueError("ATR data unavailable")
        except Exception as exc:
            logging.debug(f"[process_entry] ATR-based SL fallback failed: {exc}")
            sl_pips = float(env_loader.get_env("INIT_SL_PIPS", "20"))
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
