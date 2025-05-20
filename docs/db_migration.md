# Database Migration

The `trades` table now stores the full AI response for each entry or exit.
A new column `ai_response` has been added.

## Updating an existing `trades.db`

Run the migration helper to add the new column if your database was created
with an earlier version:

```bash
python - <<'PY'
from backend.logs.log_manager import init_db
init_db()
PY
```

This will create the `ai_response` column when missing.  Alternatively you can
execute the SQL below manually:

```sql
ALTER TABLE trades ADD COLUMN ai_response TEXT;
```
