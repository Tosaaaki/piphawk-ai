import os
import requests
from dotenv import load_dotenv
from backend.logs.log_manager import get_db_connection
from datetime import datetime, timedelta
import json

load_dotenv('./backend/config/secret.env')

OANDA_API_KEY = os.getenv('OANDA_API_KEY')
OANDA_ACCOUNT_ID = os.getenv('OANDA_ACCOUNT_ID')
OANDA_API_URL = "https://api-fxtrade.oanda.com"

headers = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

def fetch_transactions(url, params=None):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch transactions: {response.text}")
    return response.json()

def initial_fetch_oanda_trades():
    conn = get_db_connection()
    cursor = conn.cursor()

    base_url = f"{OANDA_API_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/transactions"
    params = {
        "type": "ORDER_FILL,STOP_LOSS_ORDER,TAKE_PROFIT_ORDER,MARKET_ORDER",
        "from": (datetime.utcnow() - timedelta(days=100)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pageSize": 1000
    }

    print(f"Fetching 100 days transactions from URL: {base_url} with params: {params}")

    try:
        transactions_data = fetch_transactions(base_url, params)
        transactions = transactions_data.get('transactions', [])
        print(f"Fetched {len(transactions)} transactions from API.")

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

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO oanda_trades (trade_id, instrument, units, open_time, price)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (trade_id, instrument, units, open_time, price)
                )

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

            updated_count += cursor.rowcount

        conn.commit()
        print(f"Successfully updated {updated_count} trades.")
    except Exception as e:
        print(f"Error updating trades: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    initial_fetch_oanda_trades()