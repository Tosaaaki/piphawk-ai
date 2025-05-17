import os
import logging
import requests
from dotenv import load_dotenv
from backend.logs.log_manager import get_db_connection

load_dotenv('./backend/config/secret.env')

OANDA_API_KEY = os.getenv('OANDA_API_KEY')
OANDA_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')
OANDA_API_URL = "https://api-fxtrade.oanda.com"

headers = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

logger = logging.getLogger(__name__)

def fetch_transactions(url, params=None):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch transactions: {response.text}")
    return response.json()

# Get the last transaction ID from the database
def get_last_transaction_id():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(CAST(trade_id AS INTEGER)) FROM oanda_trades")
    last_id = cursor.fetchone()[0]
    conn.close()
    return last_id if last_id else '0'

def fetch_trade_details(trade_id):
    url = f"{OANDA_API_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

import time
import json

def update_oanda_trades():
    conn = get_db_connection()
    cursor = conn.cursor()

    last_transaction_id = get_last_transaction_id()
    logger.info(f"Last transaction ID fetched from DB: {last_transaction_id}")

    base_url = f"{OANDA_API_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/transactions/sinceid"
    params = {
        "type": "ORDER_FILL,STOP_LOSS_ORDER,TAKE_PROFIT_ORDER",
        "id": str(int(last_transaction_id) + 1)
    }

    logger.info(f"Making API request to URL: {base_url} with params: {params}")

    try:
        transactions_data = fetch_transactions(base_url, params)
        transactions = transactions_data.get('transactions', [])
        logger.debug("Transactions fetched from API: %s", transactions)
        logger.debug("Fetched transactions: %s", json.dumps(transactions, indent=2))

        updated_count = 0
        for transaction in transactions:
            transaction_type = transaction['type']
            transaction_id = transaction.get('id')
            open_time = transaction.get('time', '')

            if transaction_type == 'ORDER_FILL':
                trade_id = transaction_id
                instrument = transaction.get('instrument', 'UNKNOWN')
                units = transaction.get('units', 0)
                price = transaction.get('price', 0.0)
                realized_pl = float(transaction.get('pl', 0.0))

                logger.debug("Debug BEFORE INSERT: %s %s %s %s %s %s", trade_id, instrument, units, open_time, price, realized_pl)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO oanda_trades (trade_id, instrument, units, open_time, price, realized_pl)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (trade_id, instrument, units, open_time, price, realized_pl)
                )
                logger.debug("Debug AFTER INSERT rowcount: %s", cursor.rowcount)

            elif transaction_type in ('STOP_LOSS_ORDER', 'TAKE_PROFIT_ORDER'):
                trade_id = transaction.get('tradeID') or transaction.get('tradesClosed', [{}])[0].get('tradeID')
                price = float(transaction.get('price', 0.0))
                close_time = transaction.get('time', '')
                realized_pl = float(transaction.get('tradesClosed', [{}])[0].get('realizedPL', 0.0))

                if transaction_type == 'TAKE_PROFIT_ORDER':
                    cursor.execute(
                        """
                        UPDATE oanda_trades
                        SET close_time = ?, tp_price = ?, realized_pl = ?
                        WHERE trade_id = ?
                        """,
                        (close_time, price, realized_pl, trade_id)
                    )

                elif transaction_type == 'STOP_LOSS_ORDER':
                    cursor.execute(
                        """
                        UPDATE oanda_trades
                        SET close_time = ?, sl_price = ?, realized_pl = ?
                        WHERE trade_id = ?
                        """,
                        (close_time, price, realized_pl, trade_id)
                    )

                logger.info(f"{transaction_type} updated for trade_id {trade_id}, rowcount={cursor.rowcount}")

            logger.info(f"{transaction_type} processed for trade_id {transaction_id}, rowcount={cursor.rowcount}")
            updated_count += cursor.rowcount

        conn.commit()
        logger.info(f"Successfully updated {updated_count} new trades.")
    except Exception as e:
        logger.error(f"Error updating trades: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_oanda_trades()
