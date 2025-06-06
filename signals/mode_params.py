from __future__ import annotations

import os
from pathlib import Path
import yaml

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config/mode_thresholds.yml"

_params: dict | None = None


def get_params() -> dict:
    global _params
    if _params is None:
        path = Path(os.getenv("MODE_CONFIG", _DEFAULT_PATH))
        try:
            with path.open("r", encoding="utf-8") as f:
                _params = yaml.safe_load(f) or {}
        except Exception:
            _params = {}
    return _params


def reload_params(path: str | Path | None = None) -> None:
    global _params
    if path is None:
        path = os.getenv("MODE_CONFIG", _DEFAULT_PATH)
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as f:
            _params = yaml.safe_load(f) or {}
    except Exception:
        _params = {}

__all__ = ["get_params", "reload_params"]
