from backend.strategy.openai_analysis import get_entry_decision
from backend.orders.order_manager import OrderManager
from backend.logs.log_manager import log_trade
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import json

load_dotenv()

order_manager = OrderManager()

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
    """
    Ask OpenAI whether to enter and, if yes, retrieve tp/sl in pips.
    strategy_params is enriched with tp_pips / sl_pips for use by OrderManager.
    """
    ai_response = get_entry_decision(market_data, strategy_params, indicators, market_cond)

    # --- Robustly parse AI response (dict or JSON string) ---
    if isinstance(ai_response, dict):
        resp = ai_response
    elif isinstance(ai_response, str):
        try:
            resp = json.loads(ai_response)
        except json.JSONDecodeError:
            logging.warning("Entry AI response not JSON; skipping entry.")
            return False
    else:
        logging.warning("Entry AI response unrecognized type; skipping entry.")
        return False

    ai_raw = json.dumps(resp)
    logging.info(f"AI Entry raw: {ai_raw}")
    logging.debug(f"process_entry parsed resp: {resp}")

    side = resp.get("side", "no").lower()
    if side not in ("long", "short"):
        logging.info("AI says no trade entry -> early exit in process_entry")
        return False
    logging.info(f"AI Entry side = {side}")

    tp_pips = resp.get("tp_pips")
    sl_pips = resp.get("sl_pips")
    logging.info(f"AI Entry {side} – tp={tp_pips} sl={sl_pips} (pips)")

    # --- Determine the trading instrument (currency pair) ---
    if isinstance(market_data, dict):
        instrument = market_data["prices"][0]["instrument"]
    else:
        instrument = os.getenv("DEFAULT_PAIR", "USD_JPY")

    params = {
        **strategy_params,
        "instrument": instrument,
        "side": side,
        "tp_pips": tp_pips,
        "sl_pips": sl_pips,
    }

    trade_result = order_manager.enter_trade(
        side=side,
        lot_size=float(os.getenv("TRADE_LOT_SIZE", "1.0")),
        market_data=market_data,
        strategy_params=params
    )

    if trade_result:
        instrument = params["instrument"]
        lot_size = float(os.getenv("TRADE_LOT_SIZE", "1.0"))
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_price = float(market_data['prices'][0]['bids'][0]['price'])
        entry_time = datetime.utcnow().isoformat()
        log_trade(instrument, entry_time, entry_price, units, ai_reason=ai_raw)

    return True
