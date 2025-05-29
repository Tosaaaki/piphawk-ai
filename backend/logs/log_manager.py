import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "trades.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oanda_trades (
                trade_id INTEGER PRIMARY KEY,
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
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_time TEXT,
                exit_price REAL,
                units INTEGER NOT NULL,
                profit_loss REAL,
                tp_pips REAL,
                sl_pips REAL,
                rrr REAL,
                ai_reason TEXT,
                ai_response TEXT,
                entry_regime TEXT
            )
        ''')

        # ---- simple migration for older DBs ----
        cursor.execute("PRAGMA table_info(trades)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'ai_response' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN ai_response TEXT')
        if 'tp_pips' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN tp_pips REAL')
        if 'sl_pips' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN sl_pips REAL')
        if 'rrr' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN rrr REAL')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                instrument TEXT NOT NULL,
                ai_response TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                module TEXT NOT NULL,
                error_message TEXT NOT NULL,
                additional_info TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS param_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                param_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                reason TEXT
            )
        ''')

        cursor.execute("PRAGMA table_info(param_changes)")
        param_cols = [row[1] for row in cursor.fetchall()]
        if 'reason' not in param_cols:
            cursor.execute('ALTER TABLE param_changes ADD COLUMN reason TEXT')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_details TEXT
            )
        ''')

def log_trade(
    instrument,
    entry_time,
    entry_price,
    units,
    ai_reason,
    ai_response=None,
    entry_regime=None,
    exit_time=None,
    exit_price=None,
    profit_loss=None,
    tp_pips=None,
    sl_pips=None,
    rrr=None,
):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (
                instrument, entry_time, entry_price, units,
                ai_reason, ai_response, entry_regime,
                exit_time, exit_price, profit_loss,
                tp_pips, sl_pips, rrr
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            instrument,
            entry_time,
            entry_price,
            units,
            ai_reason,
            ai_response,
            entry_regime,
            exit_time,
            exit_price,
            profit_loss,
            tp_pips,
            sl_pips,
            rrr,
        ))

def log_ai_decision(decision_type, instrument, ai_response):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_decisions (timestamp, decision_type, instrument, ai_response)
            VALUES (?, ?, ?, ?)
        ''', (datetime.utcnow().isoformat(), decision_type, instrument, ai_response))

def log_error(module, error_message, additional_info=None):
    """Record an error event.

    `error_message` can include values like errorCode and errorMessage from
    HTTP responses. Anything passed in `additional_info` is stored verbatim for
    later inspection.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO errors (timestamp, module, error_message, additional_info)
            VALUES (?, ?, ?, ?)
        ''',
            (datetime.utcnow().isoformat(), module, error_message, additional_info),
        )

def log_param_change(param_name, old_value, new_value, ai_reason):
    """
    Record a parameter change into the param_changes table.

    Args:
        param_name (str): Name of the parameter adjusted.
        old_value (Any): Original value (stored as string, may be None).
        new_value (Any): New value (stored as string).
        ai_reason (str): Reason provided by the AI or subsystem.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO param_changes (
                timestamp, param_name, old_value, new_value, reason
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            str(param_name),
            str(old_value),
            str(new_value),
            str(ai_reason),
        ))


# OANDAトレードの記録
def log_oanda_trade(trade_id, instrument, open_time, open_price, units, state, unrealized_pl, realized_pl=None, close_time=None, close_price=None, tp_price=None, sl_price=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO oanda_trades (
                trade_id, instrument, open_time, open_price, units, state, unrealized_pl, realized_pl, close_time, close_price, tp_price, sl_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trade_id, instrument, open_time, open_price, units, state, unrealized_pl, realized_pl, close_time, close_price, tp_price, sl_price))
