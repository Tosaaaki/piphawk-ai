from __future__ import annotations

"""Offline reinforcement learning policy loader."""

import logging
import pickle
from pathlib import Path
from typing import Any, Dict


logger = logging.getLogger(__name__)


class OfflinePolicy:
    """Simple wrapper around a pickled policy object."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.model: Any | None = None
        self.load()

    def load(self) -> None:
        """Load policy from pickle file if available."""
        if not self.path.exists():
            logger.warning("OfflinePolicy file not found: %s", self.path)
            self.model = None
            return
        try:
            with open(self.path, "rb") as f:
                self.model = pickle.load(f)
            logger.info("OfflinePolicy loaded from %s", self.path)
        except Exception as exc:  # pragma: no cover - unexpected format
            logger.warning("OfflinePolicy load failed: %s", exc)
            self.model = None

    def select(self, context: Dict[str, Any]) -> str | None:
        """Return chosen strategy name for given context."""
        if self.model is None:
            return None
        try:
            if hasattr(self.model, "select"):
                return self.model.select(context)
            if callable(self.model):
                return self.model(context)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - model failure
            logger.warning("OfflinePolicy prediction failed: %s", exc)
        return None


__all__ = ["OfflinePolicy"]
