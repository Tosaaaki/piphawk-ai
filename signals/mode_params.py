from __future__ import annotations

from pathlib import Path

import yaml

from backend.utils import env_loader

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config/mode_thresholds.yml"

_params: dict | None = None


def _normalize_weights(params: dict) -> None:
    """weights項目があれば合計1となるよう正規化する"""
    weights = params.get("weights")
    if not isinstance(weights, dict):
        return
    total = sum(float(v) for v in weights.values() if v is not None)
    if total <= 0:
        return
    params["weights"] = {k: float(v) / total for k, v in weights.items()}


def get_params() -> dict:
    global _params
    if _params is None:
        path = Path(env_loader.get_env("MODE_CONFIG", _DEFAULT_PATH))
        try:
            with path.open("r", encoding="utf-8") as f:
                _params = yaml.safe_load(f) or {}
            _normalize_weights(_params)
        except Exception:
            _params = {}
    return _params


def reload_params(path: str | Path | None = None) -> None:
    global _params
    if path is None:
        path = env_loader.get_env("MODE_CONFIG", _DEFAULT_PATH)
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as f:
            _params = yaml.safe_load(f) or {}
        _normalize_weights(_params)
    except Exception:
        _params = {}

__all__ = ["get_params", "reload_params"]
