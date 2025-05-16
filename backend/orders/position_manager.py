import os
import requests
from dotenv import load_dotenv
import logging

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../config/secret.env'))

from typing import List, Dict, Any, Optional

# Load OANDA API credentials from environment variables
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_API_URL = "https://api-fxtrade.oanda.com/v3"

if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    raise EnvironmentError("OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in environment variables.")

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

def get_open_positions() -> Optional[List[Dict[str, Any]]]:
    """
    Fetch open positions for the account.
    Returns a list of open positions or None if error.
    """
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/openPositions"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("positions", [])
    except Exception as e:
        print(f"Error fetching open positions: {e}")
        return None

def get_position_details(instrument: str) -> Optional[Dict[str, Any]]:
    """
    Fetch details for a specific instrument position, including entry time.
    """
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        position_data = response.json().get("position", {})
        
        # Fetch trades to find the entry time
        trades_url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades?instrument={instrument}&state=OPEN"
        trades_response = requests.get(trades_url, headers=HEADERS, timeout=10)
        trades_response.raise_for_status()
        trades = trades_response.json().get("trades", [])
        
        # Assuming we take the earliest open trade as the entry time
        if trades:
            entry_time = min(trade['openTime'] for trade in trades)
            position_data['entry_time'] = entry_time
        else:
            position_data['entry_time'] = None
        
        return position_data

    except Exception as e:
        print(f"Error fetching position details for {instrument}: {e}")
        return None

def has_open_position(pair: str) -> bool:
    positions = get_open_positions()
    if positions:
        return any(pos['instrument'] == pair and int(pos.get('long', {}).get('units', '0')) != 0 or int(pos.get('short', {}).get('units', '0')) != 0 for pos in positions)
    return False

def close_position(pair: str, side: str) -> bool:
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/positions/{pair}/close"
    data = {"longUnits": "ALL"} if side == "long" else {"shortUnits": "ALL"}
    try:
        response = requests.put(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logging.info(f"Successfully closed {side} position for {pair}")
        return True
    except Exception as e:
        logging.error(f"Error closing {side} position for {pair}: {e}")
        return False

# Example: List all open positions (for testing)
if __name__ == "__main__":
    instrument = os.getenv('DEFAULT_PAIR', 'USD_JPY')
    if has_open_position(instrument):
        print(f"Position exists for {instrument}")
        details = get_position_details(instrument)
        print(details)
    else:
        print(f"No position exists for {instrument}")

def check_current_position(pair: str) -> Optional[Dict[str, Any]]:
    """
    指定された通貨ペアのポジションの有無をチェックし、存在する場合は詳細を返す。
    存在しない場合はNoneを返す。
    """
    if has_open_position(pair):
        return get_position_details(pair)
    else:
        return None

def move_stop_loss(trade_id: str, new_sl: float) -> bool:
    """
    Move (modify) the Stop‑Loss price for an open trade via the OANDA REST API.

    Args:
        trade_id (str): The trade ID whose SL should be modified.
        new_sl (float): The new stop‑loss price.

    Returns:
        bool: True on success, False otherwise.
    """
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}/orders"
    data = {
        "stopLoss": {
            "price": f"{new_sl:.3f}"
        }
    }
    try:
        response = requests.put(url, json=data, headers=HEADERS, timeout=10)
        response.raise_for_status()
        logging.info(f"Moved stop‑loss for trade {trade_id} → {new_sl:.3f}")
        return True
    except Exception as e:
        logging.error(f"Error moving stop‑loss for trade {trade_id}: {e}")
        return False


def update_stop_loss_if_needed(position: Dict[str, Any], new_sl_price: float) -> None:
    """
    Iterate over the open trade IDs in the given position and shift their stop‑loss
    to `new_sl_price` if it is tighter (for longs: higher / shorts: lower).

    Args:
        position (Dict[str, Any]): The position dictionary obtained via `get_position_details`.
        new_sl_price (float): Desired stop‑loss price (absolute price, not pips).
    """
    if not position:
        return

    # Determine side and extract trade IDs
    if int(position.get("long", {}).get("units", "0")) != 0:
        side_key = "long"
        comparison = lambda current, new: new > current  # tighten upwards for longs
    elif int(position.get("short", {}).get("units", "0")) != 0:
        side_key = "short"
        comparison = lambda current, new: new < current  # tighten downwards for shorts
    else:
        return  # flat – nothing to do

    trade_ids = position.get(side_key, {}).get("tradeIDs", [])
    if not trade_ids:
        return

    # For each trade, fetch current SL and adjust if the new price is tighter
    for trade_id in trade_ids:
        try:
            trade_url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}"
            trade_resp = requests.get(trade_url, headers=HEADERS, timeout=10)
            trade_resp.raise_for_status()
            trade = trade_resp.json().get("trade", {})
            current_sl = float(trade.get("stopLossOrder", {}).get("price", "0"))

            if current_sl == 0 or comparison(current_sl, new_sl_price):
                move_stop_loss(trade_id, new_sl_price)
        except Exception as e:
            logging.error(f"Could not evaluate SL for trade {trade_id}: {e}")