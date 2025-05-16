from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path(__file__).resolve().parents[1] / 'config' / 'secret.env'
load_dotenv(dotenv_path)

import requests
import os
import sqlite3
from datetime import datetime, timedelta
import backend.logs.log_manager

def fetch_oanda_trades():
    api_key = os.getenv('OANDA_API_KEY')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    print(f"Using account_id: {account_id}")
    url = f'https://api-fxtrade.oanda.com/v3/accounts/{account_id}/transactions'
    params = {
        'type': 'ORDER_FILL',
        'from': (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'to': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'pageSize': 1000
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch trades: {response.text}")

def create_oanda_trades_table(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oanda_trades (
            id TEXT PRIMARY KEY,
            instrument TEXT,
            price REAL,
            open_time TEXT,
            initial_units INTEGER,
            initial_margin_required REAL,
            state TEXT,
            current_units INTEGER,
            realized_pl REAL,
            financing REAL,
            dividend_adjustment REAL,
            unrealized_pl REAL,
            margin_used REAL,
            take_profit_price REAL,
            stop_loss_price REAL,
            last_transaction_id TEXT
        );
    ''')
    conn.commit()
    conn.close()

def fetch_and_store_transactions():
    conn = sqlite3.connect('backend/logs/trades.db')
    cursor = conn.cursor()

    initial_response = fetch_oanda_trades()
    pages = initial_response.get('pages', [])
    api_key = os.getenv('OANDA_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    for page_url in pages:
        response = requests.get(page_url, headers=headers)
        transactions = response.json().get('transactions', [])

        for transaction in transactions:
            cursor.execute('''
                INSERT OR IGNORE INTO oanda_trades (
                    id, instrument, price, open_time, initial_units, realized_pl
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                transaction['id'],
                transaction.get('instrument', 'UNKNOWN'),
                float(transaction.get('price', 0)),
                transaction.get('time', ''),
                int(transaction.get('units', 0)),
                float(transaction.get('pl', 0))
            ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_oanda_trades_table('backend/logs/trades.db')
    fetch_and_store_transactions()