from __future__ import annotations

"""Simple trade mode detector with YAML configurable thresholds."""

from pathlib import Path
import yaml

from backend.utils import env_loader

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "mode_detector.yml"

_DEFAULT_PARAMS = {
    "adx_trend_min": 25,
    "adx_range_max": 18,
    "atr_pct_min": 0.003,
    "ema_slope_min": 0.1,
}

_PARAMS: dict | None = None


def _load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception:
        return {}


def load_config(path: str | Path | None = None) -> dict:
    """Return detector thresholds from YAML with defaults applied."""
    global _PARAMS
    if path is None:
        path = env_loader.get_env("MODE_DETECTOR_CONFIG", str(_DEFAULT_PATH))
    p = Path(path)
    cfg = _load_yaml(p)
    merged = {**_DEFAULT_PARAMS, **cfg}
    _PARAMS = merged
    return merged


__all__ = ["load_config"]
