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
    regime TEXT,
    exit_reason TEXT,
    is_manual INTEGER,
    forced INTEGER,
    score_version INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS ai_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    instrument TEXT NOT NULL,
    ai_response TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    module TEXT NOT NULL,
    error_message TEXT NOT NULL,
    additional_info TEXT
);
CREATE TABLE IF NOT EXISTS param_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    param_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS user_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_details TEXT
);
CREATE TABLE IF NOT EXISTS entry_skips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    instrument TEXT NOT NULL,
    side TEXT,
    reason TEXT,
    details TEXT
);
CREATE TABLE IF NOT EXISTS policy_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    state TEXT NOT NULL,
    action TEXT NOT NULL,
    reward REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS trade_labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

-- Tick data and archive tables
CREATE TABLE IF NOT EXISTS ticks (
    timestamp TEXT NOT NULL,
    instrument TEXT NOT NULL,
    bid REAL,
    ask REAL
);
CREATE TABLE IF NOT EXISTS ticks_archive (
    timestamp TEXT NOT NULL,
    instrument TEXT NOT NULL,
    bid REAL,
    ask REAL
);

-- Weekly summary view of archived ticks
CREATE VIEW IF NOT EXISTS weekly_tick_summary AS
SELECT
    strftime('%Y-%W', timestamp) AS week,
    instrument,
    COUNT(*) AS tick_count
FROM ticks_archive
WHERE timestamp >= date('now', '-4 weeks')
GROUP BY week, instrument
ORDER BY week DESC;
