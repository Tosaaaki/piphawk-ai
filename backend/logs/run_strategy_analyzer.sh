#!/usr/bin/env bash
#
# Run the hourly strategy‑analyzer from *any* location
# (works for cron as well as interactive usage).

# ── move to project root: this script sits in backend/logs/, so two levels up
cd "$(dirname "$0")/../.." || {
  echo "❌ Could not cd to project root"; exit 1;
}

# ── make sure project root is on PYTHONPATH (cron-friendly)
export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# ── activate venv if it exists and we are not already inside it
if [ -f ".venv/bin/activate" ] && [[ -z "$VIRTUAL_ENV" ]]; then
  source .venv/bin/activate
fi

# ── run analyzer; forward all CLI args (useful for debugging)
python -m backend.strategy.strategy_analyzer "$@"
