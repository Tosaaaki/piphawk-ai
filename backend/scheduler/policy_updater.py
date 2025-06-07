"""Background updater for offline policy files."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from backend.utils import env_loader
from piphawk_ai.policy.offline import OfflinePolicy

logger = logging.getLogger(__name__)


class PolicyUpdater(threading.Thread):
    """Periodically reload OfflinePolicy from file and apply to a StrategySelector."""

    def __init__(self, runner: "JobRunner", interval_min: int | None = None) -> None:
        super().__init__(daemon=True)
        self.runner = runner
        self.interval_min = interval_min or int(env_loader.get_env("POLICY_RELOAD_MIN", "5"))
        self.path = Path(env_loader.get_env("POLICY_PATH", "policies/latest_policy.pkl"))
        self._stop = False
        self.last_mtime = 0.0

    def run(self) -> None:  # pragma: no cover - background thread
        while not self._stop:
            try:
                if self.path.exists():
                    mtime = self.path.stat().st_mtime
                    if mtime != self.last_mtime:
                        policy = OfflinePolicy(self.path)
                        if policy.model is not None:
                            self.runner.current_policy = policy
                            self.last_mtime = mtime
                            logger.info("OfflinePolicy reloaded from %s", self.path)
                time.sleep(self.interval_min * 60)
            except Exception as exc:
                logger.warning("PolicyUpdater error: %s", exc)
                time.sleep(self.interval_min * 60)

    def stop(self) -> None:
        self._stop = True


__all__ = ["PolicyUpdater"]
