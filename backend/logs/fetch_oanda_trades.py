from backend.utils import env_loader

# env_loader automatically loads default env files at import time
# 旧バージョン互換用のトレード取得スクリプト
# log_manager.py のテーブル構造に合わせて列名を統一する

import requests
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import backend.logs.log_manager

_BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", str(_BASE_DIR / "trades.db")))

def fetch_oanda_trades():
    api_key = env_loader.get_env('OANDA_API_KEY')
    account_id = env_loader.get_env('OANDA_ACCOUNT_ID')
    print(f"Using account_id: {account_id}")
    url = f'https://api-fxtrade.oanda.com/v3/accounts/{account_id}/transactions'
    params = {
        'type': 'ORDER_FILL',
        'from': (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'to': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            trade_id INTEGER PRIMARY KEY,
            account_id TEXT,
            instrument TEXT NOT NULL,
            open_time TEXT NOT NULL,
            close_time TEXT,
            open_price REAL NOT NULL,
            close_price REAL,
            units INTEGER NOT NULL,
            realized_pl REAL,
            unrealized_pl REAL,
            state TEXT NOT NULL,
            tp_price REAL,
            sl_price REAL
        );
    ''')
    conn.commit()
    conn.close()

def fetch_and_store_transactions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    initial_response = fetch_oanda_trades()
    pages = initial_response.get('pages', [])
    api_key = env_loader.get_env('OANDA_API_KEY')
    account_id = env_loader.get_env('OANDA_ACCOUNT_ID')
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
                    trade_id, account_id, instrument, open_time,
                    open_price, units, state, unrealized_pl, realized_pl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction['id'],
                account_id,
                transaction.get('instrument', 'UNKNOWN'),
                transaction.get('time', ''),
                float(transaction.get('price', 0)),
                int(transaction.get('units', 0)),
                'OPEN',
                0.0,
                float(transaction.get('pl', 0))
            ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_oanda_trades_table(DB_PATH)
    fetch_and_store_transactions()
