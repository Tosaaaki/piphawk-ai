# Database Migration

The `trades` table now stores the full AI response for each entry or exit.
A new column `ai_response` has been added.  
Additionally the table tracks take‑profit and stop‑loss distances (`tp_pips`,
`sl_pips`) and the calculated risk‑reward ratio (`rrr`).

## Updating an existing `trades.db`

Run the migration helper to add the new column if your database was created
with an earlier version:

```bash
python - <<'PY'
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
