from backend.strategy.openai_analysis import get_trade_plan
from backend.orders.order_manager import OrderManager
from backend.logs.log_manager import log_trade
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import json
import uuid
from backend.utils.oanda_client import get_pending_entry_order  # helper to query OANDA pending orders

load_dotenv()

order_manager = OrderManager()

# In‑memory cache: entry_uuid -> {"instrument": str, "order_id": str, "ts": int}
_pending_limits: dict[str, dict] = {}

def process_entry(indicators, candles, market_data, market_cond: dict | None = None, strategy_params=None):
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
    plan = get_trade_plan(market_data, indicators or {}, candles or [])

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
    valid_sec = int(entry_info.get("valid_for_sec", os.getenv("MAX_LIMIT_AGE_SEC", "180")))

    if mode == "wait":
        logging.info("AI suggests WAIT – re‑evaluate next loop.")
        return False

    tp_pips = risk_info.get("tp_pips")
    sl_pips = risk_info.get("sl_pips")
    logging.info(f"AI Entry {side} – tp={tp_pips}  sl={sl_pips} (pips)")

    # --- Determine the trading instrument (currency pair) ---
    if isinstance(market_data, dict):
        instrument = market_data["prices"][0]["instrument"]
    else:
        instrument = os.getenv("DEFAULT_PAIR", "USD_JPY")

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
        }
        result = order_manager.enter_trade(
            side=side,
            lot_size=float(os.getenv("TRADE_LOT_SIZE", "1.0")),
            market_data=market_data,
            strategy_params=params_limit,
        )
        if result:
            _pending_limits[entry_uuid] = {
                "instrument": instrument,
                "order_id": result.get("order_id"),
                "ts": int(datetime.utcnow().timestamp()),
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
        }

    trade_result = order_manager.enter_trade(
        side=side,
        lot_size=float(os.getenv("TRADE_LOT_SIZE", "1.0")),
        market_data=market_data,
        strategy_params=params
    )

    if trade_result and mode == "market":
        instrument = params["instrument"]
        lot_size = float(os.getenv("TRADE_LOT_SIZE", "1.0"))
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_price = float(market_data['prices'][0]['bids'][0]['price'])
        entry_time = datetime.utcnow().isoformat()
        log_trade(instrument, entry_time, entry_price, units, ai_reason=ai_raw)

    return True

# TODO: add a routine in JobRunner to poll OANDA pending orders,
#       check _pending_limits age, and call get_trade_plan() for renew/cancel.
