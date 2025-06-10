import logging
import requests
import sqlite3
import time
from backend.utils import env_loader
from backend.logs.log_manager import (
    get_db_connection,
    init_db,
    log_oanda_trade,
    log_error,
)

# env_loader automatically loads default env files at import time

OANDA_API_KEY = env_loader.get_env('OANDA_API_KEY')
OANDA_ACCOUNT_ID = env_loader.get_env('OANDA_ACCOUNT_ID')
OANDA_API_URL = "https://api-fxtrade.oanda.com"

headers = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

logger = logging.getLogger(__name__)


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
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch transactions: {response.text}")
    return response.json()

# Get the last transaction ID from the database
def get_last_transaction_id():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MAX(CAST(trade_id AS INTEGER)) FROM oanda_trades WHERE account_id = ?",
        (OANDA_ACCOUNT_ID,),
    )
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
        for transaction in transactions:
            rowcount = 0
            tx_type = transaction.get("type", "")
            if tx_type.endswith("_REJECT"):
                logger.warning(
                    f"\u274c {tx_type} reason={transaction.get('rejectReason')}"
                )
            if tx_type in ("TAKE_PROFIT_ORDER_REJECT", "ORDER_CANCEL"):
                logger.warning(
                    f"[DEBUG] {tx_type} rejectReason={transaction.get('rejectReason')}"
                )
            transaction_type = tx_type
            transaction_id = transaction.get('id')
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

                logger.info(f"{transaction_type} updated for trade_id {trade_id}, rowcount={rowcount}")

            logger.info(
                f"{transaction_type} processed for trade_id {transaction_id}, rowcount={rowcount}"
            )
            if transaction_type != 'ORDER_FILL':
                updated_count += rowcount

        execute_with_retry(conn.commit)
        logger.info(f"Successfully updated {updated_count} new trades.")
    except Exception as e:
        logger.error(f"Error updating trades: {e}")
        log_error("update_oanda_trades", str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    update_oanda_trades()
