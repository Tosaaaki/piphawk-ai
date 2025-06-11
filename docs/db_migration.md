# Database Migration

When running in Docker the default SQLite path is `/app/backend/logs/trades.db`.

The `trades` table now stores the full AI response for each entry or exit.
A new column `ai_response` has been added.  
Additionally the table tracks take‑profit and stop‑loss distances (`tp_pips`,
`sl_pips`) and the calculated risk‑reward ratio (`rrr`).
The `oanda_trades` table now stores the opening price in `open_price`.

## Updating an existing `trades.db`

Run the migration helper to add the new column if your database was created
with an earlier version:

```bash
python3 - <<'PY'
from backend.logs.log_manager import init_db
init_db()
PY
```

This will create any missing columns (`ai_response`, `tp_pips`, `sl_pips`,
`rrr`).  Alternatively you can execute the SQL below manually:

```sql
ALTER TABLE trades ADD COLUMN ai_response TEXT;
ALTER TABLE trades ADD COLUMN tp_pips REAL;
ALTER TABLE trades ADD COLUMN sl_pips REAL;
ALTER TABLE trades ADD COLUMN rrr REAL;
```

The `param_changes` table now records the reason for each change in the
`reason` column. To add this column to an older database run `init_db()`
again or execute:

```sql
ALTER TABLE param_changes ADD COLUMN reason TEXT;
```

The database now also includes an `errors` table to store module errors. If your existing `trades.db` lacks this table, run `init_db()` once or execute the SQL below:

```sql
CREATE TABLE errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    module TEXT NOT NULL,
    error_message TEXT NOT NULL,
    additional_info TEXT
);
```

If you run an older database without the `account_id` column in `oanda_trades`, execute `init_db()` to add it automatically or run:

```sql
ALTER TABLE oanda_trades ADD COLUMN account_id TEXT;
```

古い `oanda_trades` テーブルに `open_price` 列が無い場合も `init_db()` を実行する
だけで自動的に追加されます。手動で行う場合は以下を実行してください。

```sql
ALTER TABLE oanda_trades ADD COLUMN open_price REAL;
```

古いデータベースで `price` 列が残っている場合、`init_db()` を実行すると
`open_price` 列にその値がコピーされます。`price` 列は削除されませんが、
更新処理で値がセットされるためエラーは発生しなくなります。

## `score_version` 列の追加

`trades` テーブルはスコア計算のバージョン管理用に `score_version` 列を
持ちます。バージョン 1 以降で初めて導入されたため、既存のデータベース
ではこの列が存在しません。

以下の SQL か `init_db()` を一度実行して列を追加してください。既存行
には `1` が自動的に設定されます。

```sql
ALTER TABLE trades ADD COLUMN score_version INTEGER DEFAULT 1;
UPDATE trades SET score_version = 1;
```
