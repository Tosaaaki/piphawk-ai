"""Utilities for halting processes when loss or error counts exceed limits."""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SafetyTrigger:
    """Monitor loss and error metrics and trigger stop callbacks."""

    def __init__(self, loss_limit: float = 0.0, error_limit: int = 0, cooldown_sec: int = 0):
        self.loss_limit = loss_limit
        self.error_limit = error_limit
        self.cooldown = timedelta(seconds=cooldown_sec)
        self._loss = 0.0
        self._errors = 0
        self._stopped_at: datetime | None = None
        self._callback = None

    def attach(self, callback) -> None:
        """Set callback invoked on stop."""
        self._callback = callback

    def record_loss(self, amount: float) -> None:
        self._loss += amount
        logger.debug(f"Cumulative loss updated: {self._loss}")
        self._check()

    def record_error(self) -> None:
        self._errors += 1
        logger.debug(f"Error count updated: {self._errors}")
        self._check()

    def _check(self) -> None:
        if self._stopped_at and datetime.utcnow() - self._stopped_at < self.cooldown:
            return
        if self.loss_limit and self._loss <= -abs(self.loss_limit):
            logger.warning("Loss limit exceeded – triggering stop")
            self._trigger()
        if self.error_limit and self._errors >= self.error_limit:
            logger.warning("Error limit exceeded – triggering stop")
            self._trigger()

    def _trigger(self) -> None:
        self._stopped_at = datetime.utcnow()
        if self._callback:
            try:
                self._callback()
            except Exception as exc:  # pragma: no cover
                logger.error(f"Safety trigger callback failed: {exc}")

