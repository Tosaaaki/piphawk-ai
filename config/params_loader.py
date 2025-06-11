"""Load parameters from params.yaml and strategy.yml into environment variables."""
from __future__ import annotations

import os
from pathlib import Path
import yaml
import json

STATE_FILE = Path("/tmp/last_trade_mode.json")


def load_last_mode() -> str | None:
    """Return last trade mode stored in STATE_FILE."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text()).get("mode")
        except Exception:
            return None
    return None


def save_last_mode(mode: str) -> None:
    """Persist current trade mode to STATE_FILE."""
    try:
        STATE_FILE.write_text(json.dumps({"mode": mode}))
    except Exception:
        pass

# YAML内キーと環境変数名のマッピング
_KEY_ALIASES = {
    "RISK_MIN_ATR_SL_MULTIPLIER": "MIN_ATR_MULT",
    "RISK_MIN_RR_RATIO": "MIN_RRR",
    "FILTERS_AVOID_FALSE_BREAK_LOOKBACK_CANDLES": "FALSE_BREAK_LOOKBACK",
    "FILTERS_AVOID_FALSE_BREAK_THRESHOLD_RATIO": "FALSE_BREAK_RATIO",
    "REENTRY_TRIGGER_PIPS_OVER_BREAK": "REENTRY_TRIGGER_PIPS",
    "RUNTIME_AI_COOLDOWN_SEC_OPEN": "AI_COOLDOWN_SEC_OPEN",
    "RUNTIME_AI_COOLDOWN_SEC_FLAT": "AI_COOLDOWN_SEC_FLAT",
}


def _parse_yaml_file(path: Path) -> dict:
    """YAMLファイルを読み込み、辞書として返す"""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _flatten(d: object, prefix: str = "") -> dict[str, object]:
    flat: dict[str, object] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            key = f"{prefix}_{k}" if prefix else k
            flat.update(_flatten(v, key))
    elif isinstance(d, list):
        flat[prefix.upper()] = ",".join(str(item) for item in d)
    else:
        flat[prefix.upper()] = d
    return flat


def load_params(
    path: str | Path = Path(__file__).resolve().parent / "params.yaml",
    strategy_path: str | Path | None = Path(__file__).resolve().parent
    / "strategy.yml",
    settings_path: str | Path | None = Path(__file__).resolve().parent / "settings.yaml",
    mode_path: str | Path | None = Path(__file__).resolve().parent / "mode_thresholds.yml",
):
    """Load YAML parameters and export them as environment variables."""

    env_params: dict[str, object] = {}

    if path is not None:
        p = Path(path)
        if p.exists():
            env_params.update(_flatten(_parse_yaml_file(p)))

    if strategy_path is not None:
        sp = Path(strategy_path)
        if sp.exists():
            env_params.update(_flatten(_parse_yaml_file(sp)))

    if settings_path is not None:
        se = Path(settings_path)
        if se.exists():
            env_params.update(_flatten(_parse_yaml_file(se)))

    if mode_path is not None:
        mp = Path(mode_path)
        if mp.exists():
            env_params.update(_flatten(_parse_yaml_file(mp)))

    # キーエイリアスの適用
    for src, target in _KEY_ALIASES.items():
        if src in env_params and target not in env_params:
            env_params[target] = env_params[src]

    for k, v in env_params.items():
        os.environ[k] = str(v)
    return env_params
