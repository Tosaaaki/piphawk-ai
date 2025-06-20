import logging
import sqlite3
import time

import requests

from backend.utils import env_loader

try:
    from backend.logs.log_manager import (
        add_trade_label,
        get_db_connection,
        init_db,
        log_error,
        log_oanda_trade,
    )
except Exception:  # テスト環境では簡易版を提供
    def get_db_connection():
        return sqlite3.connect(":memory:")

    def init_db():
        pass

    def log_oanda_trade(*_a, **_k):
        pass

    def log_error(*_a, **_k):
        pass

    def add_trade_label(*_a, **_k):
        pass

# env_loader automatically loads default env files at import time

OANDA_API_KEY = env_loader.get_env('OANDA_API_KEY')
OANDA_ACCOUNT_ID = env_loader.get_env('OANDA_ACCOUNT_ID')
OANDA_API_URL = "https://api-fxtrade.oanda.com"

headers = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

logger = logging.getLogger(__name__)

# これらの拒否理由は想定内のため警告レベルにしない
IGNORE_REJECT_REASONS = {
    "TRADE_DOESNT_EXIST",
    "ORDER_DOESNT_EXIST",
    "NO_SUCH_TRADE",
    "TAKE_PROFIT_ORDER_ALREADY_EXISTS",
}


def execute_with_retry(func, *args, retries=5, delay=2, **kwargs):
    """Retry database operations when the database is locked."""
    last_exc = None
    for _ in range(retries):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as exc:
            if "database is locked" in str(exc):
                last_exc = exc
                logger.warning("Database is locked, retrying in %s seconds...", delay)
                time.sleep(delay)
                continue
            raise
    if last_exc:
        raise last_exc

def fetch_transactions(url, params=None):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.Timeout:
        logger.error("Timeout when fetching transactions from %s", url)
        raise
    except requests.RequestException as exc:
        logger.error("Error fetching transactions: %s", exc)
        raise
    if response.status_code != 200:
        raise Exception(f"Failed to fetch transactions: {response.text}")
    return response.json()

# Get the last transaction ID from the database
def get_last_transaction_id():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value FROM sync_state WHERE key = 'last_transaction_id'"
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else '0'


def set_last_transaction_id(transaction_id: str) -> None:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
        ("last_transaction_id", str(transaction_id)),
    )
    conn.commit()
    conn.close()

def fetch_trade_details(trade_id):
    url = f"{OANDA_API_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.Timeout:
        logger.error("Timeout when fetching trade details for %s", trade_id)
        raise
    except requests.RequestException as exc:
        logger.error("Error fetching trade details: %s", exc)
        raise
    if response.status_code == 200:
        return response.json()
    else:
        return None

import json


def update_oanda_trades():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    last_transaction_id = get_last_transaction_id()
    logger.info(f"Last transaction ID fetched from DB: {last_transaction_id}")

    base_url = f"{OANDA_API_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/transactions/sinceid"
    params = {
        "type": (
            "ORDER_FILL,STOP_LOSS_ORDER,TAKE_PROFIT_ORDER,"
            "STOP_LOSS_ORDER_REJECT,TAKE_PROFIT_ORDER_REJECT,"
            "ORDER_CANCEL"
        ),
        "id": str(int(last_transaction_id) + 1),
    }

    logger.info(f"Making API request to URL: {base_url} with params: {params}")

    try:
        transactions_data = fetch_transactions(base_url, params)
        transactions = transactions_data.get('transactions', [])
        logger.debug("Transactions fetched from API: %s", transactions)
        logger.debug("Fetched transactions: %s", json.dumps(transactions, indent=2))

        updated_count = 0
        max_id = int(last_transaction_id)
        for transaction in transactions:
            rowcount = 0
            tx_type = transaction.get("type", "")
            reject_reason = transaction.get("rejectReason")
            if tx_type.endswith("_REJECT"):
                if reject_reason in IGNORE_REJECT_REASONS:
                    logger.info(f"{tx_type} reason={reject_reason}")
                else:
                    logger.warning(f"\u274c {tx_type} reason={reject_reason}")
                if tx_type in ("TAKE_PROFIT_ORDER_REJECT", "ORDER_CANCEL"):
                    logger.warning(
                        f"[DEBUG] {tx_type} rejectReason={reject_reason}"
                    )
            transaction_type = tx_type
            transaction_id = transaction.get('id')
            if transaction_id and int(transaction_id) > max_id:
                max_id = int(transaction_id)
            open_time = transaction.get('time', '')

            if transaction_type == 'ORDER_FILL':
                trade_id = transaction_id
                instrument = transaction.get('instrument', 'UNKNOWN')
                units = transaction.get('units', 0)
                price = float(transaction.get('price', 0.0))
                realized_pl = float(transaction.get('pl', 0.0))

                logger.debug(
                    "Debug BEFORE INSERT: %s %s %s %s %s %s",
                    trade_id,
                    instrument,
                    units,
                    open_time,
                    price,
                    realized_pl,
                )
                execute_with_retry(
                    log_oanda_trade,
                    trade_id,
                    OANDA_ACCOUNT_ID,
                    instrument,
                    open_time,
                    price,
                    units,
                    "OPEN",
                    0.0,
                    realized_pl,
                    conn=conn,
                )
                add_trade_label(trade_id, "FILL")
                logger.debug("Debug AFTER INSERT rowcount: 1")
                rowcount = 1
                updated_count += rowcount

            elif transaction_type in ('STOP_LOSS_ORDER', 'TAKE_PROFIT_ORDER'):
                trade_id = transaction.get('tradeID') or transaction.get('tradesClosed', [{}])[0].get('tradeID')
                price = float(transaction.get('price', 0.0))
                close_time = transaction.get('time', '')
                realized_pl = float(transaction.get('tradesClosed', [{}])[0].get('realizedPL', 0.0))

                if transaction_type == 'TAKE_PROFIT_ORDER':
                    before = conn.total_changes
                    execute_with_retry(
                        cursor.execute,
                        """
                        UPDATE oanda_trades
                        SET close_time = ?, close_price = ?, tp_price = ?, realized_pl = ?, state = 'CLOSED'
                        WHERE trade_id = ?
                        """,
                        (close_time, price, price, realized_pl, trade_id),
                    )
                    rowcount = conn.total_changes - before
                    add_trade_label(trade_id, "TP")

                elif transaction_type == 'STOP_LOSS_ORDER':
                    before = conn.total_changes
                    execute_with_retry(
                        cursor.execute,
                        """
                        UPDATE oanda_trades
                        SET close_time = ?, close_price = ?, sl_price = ?, realized_pl = ?, state = 'CLOSED'
                        WHERE trade_id = ?
                        """,
                        (close_time, price, price, realized_pl, trade_id),
                    )
                    rowcount = conn.total_changes - before
                    add_trade_label(trade_id, "SL")

                logger.info(f"{transaction_type} updated for trade_id {trade_id}, rowcount={rowcount}")

            logger.info(
                f"{transaction_type} processed for trade_id {transaction_id}, rowcount={rowcount}"
            )
            if transaction_type != 'ORDER_FILL':
                updated_count += rowcount

        execute_with_retry(conn.commit)
        set_last_transaction_id(str(max_id))
        logger.info(f"Successfully updated {updated_count} new trades.")
    except Exception as e:
        logger.error(f"Error updating trades: {e}")
        log_error("update_oanda_trades", str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    update_oanda_trades()
