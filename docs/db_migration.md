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
