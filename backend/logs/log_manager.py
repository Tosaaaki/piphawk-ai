import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from backend.utils import env_loader

_BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", str(_BASE_DIR / "trades.db")))

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=30)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
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
            )
        ''')

        cursor.execute("PRAGMA table_info(oanda_trades)")
        oanda_cols = [row[1] for row in cursor.fetchall()]
        if 'account_id' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN account_id TEXT')
        # 旧バージョンのDBに open_price が無い場合に追加
        if 'open_price' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN open_price REAL')
        if 'price' in oanda_cols:
            cursor.execute('UPDATE oanda_trades SET open_price = price WHERE open_price IS NULL')
        if 'close_time' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN close_time TEXT')
        if 'close_price' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN close_price REAL')
        if 'realized_pl' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN realized_pl REAL')
        if 'unrealized_pl' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN unrealized_pl REAL')
        if 'state' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN state TEXT')
        if 'tp_price' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN tp_price REAL')
        if 'sl_price' not in oanda_cols:
            cursor.execute('ALTER TABLE oanda_trades ADD COLUMN sl_price REAL')

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
                ai_dir TEXT,
                local_dir TEXT,
                final_side TEXT,
                ai_reason TEXT,
                ai_response TEXT,
                entry_regime TEXT,
                exit_reason TEXT
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
        if 'ai_dir' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN ai_dir TEXT')
        if 'local_dir' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN local_dir TEXT')
        if 'final_side' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN final_side TEXT')
        if 'exit_reason' not in columns:
            cursor.execute('ALTER TABLE trades ADD COLUMN exit_reason TEXT')

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_skips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                instrument TEXT NOT NULL,
                side TEXT,
                reason TEXT,
                details TEXT
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
    ai_dir=None,
    local_dir=None,
    final_side=None,
    exit_reason=None,
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (
                instrument, entry_time, entry_price, units,
                ai_reason, ai_response, entry_regime,
                exit_time, exit_price, profit_loss,
                tp_pips, sl_pips, rrr,
                ai_dir, local_dir, final_side,
                exit_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ai_dir,
            local_dir,
            final_side,
            exit_reason,
        ))

def log_ai_decision(decision_type, instrument, ai_response):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_decisions (timestamp, decision_type, instrument, ai_response)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now(timezone.utc).isoformat(), decision_type, instrument, ai_response))

def log_error(module, error_message, additional_info=None):
    """Record an error event.

    `error_message` can include values like errorCode and errorMessage from
    HTTP responses. Anything passed in `additional_info` is stored verbatim for
    later inspection.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO errors (timestamp, module, error_message, additional_info)
                VALUES (?, ?, ?, ?)
            ''',
                (datetime.now(timezone.utc).isoformat(), module, error_message, additional_info),
            )
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            try:
                init_db()
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''
                        INSERT INTO errors (timestamp, module, error_message, additional_info)
                        VALUES (?, ?, ?, ?)
                    ''',
                        (datetime.now(timezone.utc).isoformat(), module, error_message, additional_info),
                    )
            except Exception as retry_exc:
                logger.warning("log_error retry failed: %s", retry_exc)
        else:
            logger.warning("log_error failed: %s", exc)
    except Exception as exc:
        logger.warning("log_error failed: %s", exc)

def log_param_change(param_name, old_value, new_value, ai_reason):
    """
    Record a parameter change into the param_changes table.

    Args:
        param_name (str): Name of the parameter adjusted.
        old_value (Any): Original value (stored as string, may be None).
        new_value (Any): New value (stored as string).
        ai_reason (str): Reason provided by the AI or subsystem.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO param_changes (
                timestamp, param_name, old_value, new_value, reason
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now(timezone.utc).isoformat(),
            str(param_name),
            str(old_value),
            str(new_value),
            str(ai_reason),
        ))


def log_entry_skip(instrument, side, reason, details=None):
    """Record an entry skip event."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO entry_skips (
                timestamp, instrument, side, reason, details
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (
                datetime.now(timezone.utc).isoformat(),
                instrument,
                side,
                reason,
                details,
            ),
        )


# OANDAトレードの記録
def log_oanda_trade(
    trade_id,
    account_id,
    instrument,
    open_time,
    open_price,
    units,
    state,
    unrealized_pl,
    realized_pl=None,
    close_time=None,
    close_price=None,
    tp_price=None,
    sl_price=None,
    conn=None,
):
    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(oanda_trades)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'price' in cols:
        cursor.execute(
            '''
                INSERT OR REPLACE INTO oanda_trades (
                    trade_id, account_id, instrument, open_time,
                    open_price, price, units, state, unrealized_pl,
                    realized_pl, close_time, close_price, tp_price, sl_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                trade_id,
                account_id,
                instrument,
                open_time,
                open_price,
                open_price,
                units,
                state,
                unrealized_pl,
                realized_pl,
                close_time,
                close_price,
                tp_price,
                sl_price,
            ),
        )
    else:
        cursor.execute(
            '''
                INSERT OR REPLACE INTO oanda_trades (
                    trade_id, account_id, instrument, open_time, open_price, units, state, unrealized_pl, realized_pl, close_time, close_price, tp_price, sl_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                trade_id,
                account_id,
                instrument,
                open_time,
                open_price,
                units,
                state,
                unrealized_pl,
                realized_pl,
                close_time,
                close_price,
                tp_price,
                sl_price,
            ),
        )
    if own_conn:
        conn.commit()
        conn.close()
