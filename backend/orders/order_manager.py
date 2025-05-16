import os
import requests
from backend.logs.log_manager import log_trade, log_error
from datetime import datetime
import time
import logging
logger = logging.getLogger(__name__)

OANDA_API_URL = os.getenv("OANDA_API_URL", "https://api-fxtrade.oanda.com/v3")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

# ----------------------------------------------------------------------
#  Pip‑size table (extend as needed) and helper
# ----------------------------------------------------------------------
DEFAULT_PAIR = os.getenv("DEFAULT_PAIR", "USD_JPY")

PIP_SIZES: dict[str, float] = {
    "USD_JPY": 0.01,
    "EUR_USD": 0.0001,
    # add more pairs here if necessary
}

def get_pip_size(instrument: str) -> float:
    """Return pip size for the instrument; fallback to DEFAULT_PAIR mapping."""
    return PIP_SIZES.get(instrument, PIP_SIZES.get(DEFAULT_PAIR, 0.01))

class OrderManager:

    def place_market_order(self, instrument, units):
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        response = requests.post(url, json=data, headers=HEADERS)
        if response.status_code != 201:
            raise Exception(f"Failed to place order: {response.text}")
        return response.json()

    def adjust_tp_sl(self, instrument, trade_id, new_tp=None, new_sl=None):
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}/orders"
        body = {"order": {}}
        if new_tp:
            body["order"]["takeProfit"] = {"price": str(new_tp)}
        if new_sl:
            body["order"]["stopLoss"] = {"price": str(new_sl)}

        for attempt in range(3):
            response = requests.put(url, json=body, headers=HEADERS)
            if response.status_code == 200:
                return response.json()
            elif "NO_SUCH_TRADE" in response.text or "ORDER_DOESNT_EXIST" in response.text:
                log_error("order_manager", f"TP/SL adjustment failed: trade not found", response.text)
                break
            else:
                time.sleep(1)
        log_error("order_manager", "TP/SL adjustment failed after retries", response.text)
        return None

    def market_close_position(self, instrument):
        # delegate to unified close_position() helper
        logger.debug(f"[market_close_position] closing BOTH sides for {instrument}")
        return self.close_position(instrument, side="both")

    def enter_trade(self, lot_size, market_data, strategy_params, side="long"):
        min_lot = float(os.getenv("MIN_TRADE_LOT", "0.01"))
        max_lot = float(os.getenv("MAX_TRADE_LOT", "0.1"))
        lot_size = max(min_lot, min(lot_size, max_lot))

        instrument = strategy_params["instrument"]
        tp_pips = strategy_params.get("tp_pips")
        sl_pips = strategy_params.get("sl_pips")
        pip = get_pip_size(instrument)
        # side = strategy_params.get("side", "long").lower()

        entry_price = float(market_data['prices'][0]['bids'][0]['price']) if side == "long" else float(market_data['prices'][0]['asks'][0]['price'])
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_time = datetime.utcnow().isoformat()

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        order_body = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }

        if tp_pips and sl_pips:
            if side == "long":
                tp_price = round(entry_price + float(tp_pips) * pip, 3)
                sl_price = round(entry_price - float(sl_pips) * pip, 3)
            else:
                tp_price = round(entry_price - float(tp_pips) * pip, 3)
                sl_price = round(entry_price + float(sl_pips) * pip, 3)

            order_body["order"]["takeProfitOnFill"] = {"price": str(tp_price)}
            order_body["order"]["stopLossOnFill"] = {"price": str(sl_price)}

        response = requests.post(url, json=order_body, headers=HEADERS)
        if response.status_code != 201:
            raise Exception(f"Failed to place order: {response.text}")

        result = response.json()
        log_trade(instrument, entry_time, entry_price, units, strategy_params.get("ai_reason", "manual"), side.upper())
        return result

    def exit_trade(self, position):
        instrument = position["instrument"]
        units_val = float(position.get("units", 0))
        # log raw position info before side detection
        logger.debug(f"[exit_trade] raw units={units_val} position={position}")

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch position details: {response.text}")

        position_data = response.json()['position']
        long_units = int(position_data['long']['units'])
        short_units = int(position_data['short']['units'])

        if short_units < 0:
            side = "short"
        elif long_units > 0:
            side = "long"
        else:
            side = "both"

        logger.debug(f"[exit_trade] API-based detected side={side} for {instrument}")
        result = self.close_position(instrument, side)

        entry_price = float(position['long']['averagePrice'] if int(position['long']['units']) > 0 else position['short']['averagePrice'])

        if side == "long":
            units = int(position['long']['units'])
        elif side == "short":
            units = int(position['short']['units'])
        else:
            units = 0

        log_trade(
            instrument=instrument,
            entry_time=position.get('entry_time', datetime.utcnow().isoformat()),
            entry_price=entry_price,
            units=units,
            ai_reason="exit",
            exit_time=datetime.utcnow().isoformat()
        )
        return result

    def close_position(self, instrument, side: str = "both"):
        if side is None:
            raise ValueError("side must be 'long', 'short', or 'both'")
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}/close"

        # OANDA spec: we must explicitly specify which side(s) to close
        if side == "short":
            payload = {"shortUnits": "ALL"}
        elif side == "long":
            payload = {"longUnits": "ALL"}
        else:
            # close both sides explicitly
            payload = {"longUnits": "ALL", "shortUnits": "ALL"}

        logger.debug(f"[close_position] payload={payload}")
        response = requests.put(url, json=payload, headers=HEADERS)

        if not response.ok:
            raise Exception(f"Failed to close position: {response.text}")

        return response.json()

    # --- Trailing‑Stop helper -------------------------------------------------
    def place_trailing_stop(
        self,
        trade_id: str,
        instrument: str,
        distance_pips: int | None = None,
    ) -> dict:
        """
        Send a TRAILING_STOP_LOSS order for the given trade.

        Args:
            trade_id (str): OANDA tradeID you want to attach the trailing stop to.
            instrument (str): e.g. “USD_JPY”.
            distance_pips (int, optional): Stop distance in pips.  If omitted,
                reads the environment variable TRAIL_DISTANCE_PIPS (default 6).

        Returns:
            dict: OANDA API JSON response.
        """
        if distance_pips is None:
            distance_pips = int(os.getenv("TRAIL_DISTANCE_PIPS", 6))

        # Convert pips to price distance (JPY pairs use 0.01, most majors 0.0001)
        pip_factor = 0.01 if instrument.endswith("JPY") else 0.0001
        distance_price = round(distance_pips * pip_factor, 5)

        order_spec = {
            "order": {
                "type": "TRAILING_STOP_LOSS",
                "tradeID": trade_id,
                "distance": str(distance_price),
                "timeInForce": "GTC",
            }
        }

        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/orders"
        response = requests.post(url, json=order_spec, headers=HEADERS)
        response.raise_for_status()
        return response.json()

    def update_trade_sl(self, trade_id, instrument, new_sl_price):
        url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}/orders"
        body = {"order": {"stopLoss": {"price": str(new_sl_price), "timeInForce": "GTC"}}}

        response = requests.put(url, json=body, headers=HEADERS)

        if response.status_code != 200:
            log_error("order_manager", f"Failed to update SL: {response.text}")
            return None

        log_trade(instrument, datetime.utcnow().isoformat(), new_sl_price, 0, "SL dynamically updated", "SL_UPDATE")
        return response.json()
