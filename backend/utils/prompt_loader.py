"""Prompt template loader utility."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_template(name: str) -> str:
    """Return prompt template text or empty string on failure."""
    try:
        with open(_BASE_DIR / name, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as exc:  # pragma: no cover - file issues
        logger.error("Failed to load template %s: %s", name, exc)
        return ""

__all__ = ["load_template"]
