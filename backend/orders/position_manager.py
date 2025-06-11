import requests
from backend.utils import env_loader
from backend.utils.http_client import request_with_retries
import logging
import time

logger = logging.getLogger(__name__)
import json

# env_loader automatically loads default env files at import time

from typing import List, Dict, Any, Optional

# Load OANDA API credentials from environment variables
OANDA_API_KEY = env_loader.get_env("OANDA_API_KEY")
OANDA_ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
OANDA_API_URL = "https://api-fxtrade.oanda.com/v3"

if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    raise EnvironmentError("OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in environment variables.")

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json",
}


def get_margin_used(retries: int = 2, delay: float = 1.0) -> Optional[float]:
    """Return current marginUsed from account summary."""
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/summary"
    try:
        resp = request_with_retries("get", url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        account = resp.json().get("account", {})
        return float(account.get("marginUsed", 0.0))
    except Exception as exc:
        logger.warning(f"get_margin_used failed: {exc}")
        return None

def get_account_balance(retries: int = 2, delay: float = 1.0) -> Optional[float]:
    """Return current account balance."""
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/summary"
    try:
        resp = request_with_retries("get", url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        account = resp.json().get("account", {})
        return float(account.get("balance", 0.0))
    except Exception as exc:
        logger.warning(f"get_account_balance failed: {exc}")
        return None

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
        logger.error(f"Error fetching open positions: {e}")
        return None

def get_position_details(instrument: str) -> Optional[Dict[str, Any]]:
    """
    指定銘柄のポジション詳細を取得する。エントリ時のコメントから
    tp/sl(pips) も抽出し ``tp_pips`` / ``sl_pips`` として返す。
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

        # ---- calc total PL from individual trades -----------------------
        pl_total = 0.0
        for tr in trades:
            try:
                units = float(tr.get("currentUnits", 0))
                open_price = float(tr.get("price", 0))
                unreal = float(tr.get("unrealizedPL", 0))
                realized = float(tr.get("realizedPL", 0))
                _ = units, open_price  # 明示的な使用で型チェックを回避
                pl_total += unreal + realized
            except Exception:
                pass
        position_data["pl_corrected"] = pl_total

        # ---- extract entry_regime JSON from clientExtensions.comment ----
        entry_regime = None
        tp_comment = None
        sl_pips = None
        tp_pips = None
        for tr in trades:
            comment = tr.get("clientExtensions", {}).get("comment")
            if comment:
                try:
                    entry_regime = json.loads(comment)
                    sl_pips = entry_regime.get("sl")
                    tp_pips = entry_regime.get("tp")
                except json.JSONDecodeError:
                    entry_regime = {"regime": "unknown"}
                break
        for tr in trades:
            tp_comment = (
                tr.get("takeProfitOrder", {})
                .get("clientExtensions", {})
                .get("comment")
            )
            if tp_comment:
                break
        position_data["entry_regime"] = json.dumps(entry_regime) if entry_regime else None
        position_data["tp_comment"] = tp_comment
        if sl_pips is not None:
            position_data["sl_pips"] = float(sl_pips)
        if tp_pips is not None:
            position_data["tp_pips"] = float(tp_pips)

        return position_data

    except Exception as e:
        logger.error(f"Error fetching position details for {instrument}: {e}")
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
    instrument = env_loader.get_env('DEFAULT_PAIR', 'USD_JPY')
    if has_open_position(instrument):
        logger.info(f"Position exists for {instrument}")
        details = get_position_details(instrument)
        logger.info(details)
    else:
        logger.info(f"No position exists for {instrument}")

def check_current_position(pair: str) -> Optional[Dict[str, Any]]:
    """
    指定された通貨ペアのポジションの有無をチェックし、存在する場合は詳細を返す。
    存在しない場合はNoneを返す。
    """
    if has_open_position(pair):
        return get_position_details(pair)
    else:
        return None

def move_stop_loss(trade_id: str, instrument: str, new_sl: float) -> bool:
    """Move the stop loss for an open trade via ``update_trade_sl``."""
    try:
        from backend.orders.order_manager import OrderManager

        result = OrderManager().update_trade_sl(trade_id, instrument, new_sl)
        if result is not None:
            logging.info(f"Moved stop‑loss for trade {trade_id} → {new_sl:.3f}")
            return True
        logging.error(f"SL update returned None for trade {trade_id}")
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

    # ショートポジションを先に評価する
    if int(position.get("short", {}).get("units", "0")) != 0:
        side_key = "short"
        comparison = lambda current, new: new < current  # tighten downwards for shorts
    elif int(position.get("long", {}).get("units", "0")) != 0:
        side_key = "long"
        comparison = lambda current, new: new > current  # tighten upwards for longs
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
                move_stop_loss(trade_id, position.get("instrument", ""), new_sl_price)
        except Exception as e:
            logging.error(f"Could not evaluate SL for trade {trade_id}: {e}")
