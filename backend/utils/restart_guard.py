"""Restart guard to prevent excessive self-restarts."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from . import env_loader

_STATE_PATH = Path(env_loader.get_env("RESTART_STATE_PATH", "/tmp/piphawk_last_restart"))


def can_restart(interval: float) -> bool:
    """Return True if enough time has passed since the last restart."""
    now = time.time()
    try:
        last = float(_STATE_PATH.read_text())
    except Exception:
        last = 0.0
    if now - last >= interval:
        try:
            _STATE_PATH.write_text(str(now))
        except Exception as exc:  # pragma: no cover - best effort
            logging.getLogger(__name__).warning("Failed to record restart time: %s", exc)
        return True
    return False
