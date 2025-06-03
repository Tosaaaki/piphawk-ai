"""params.yaml を読み込み環境変数へ反映する簡易ローダー."""
from __future__ import annotations

import os
from pathlib import Path


def _parse_value(val: str):
    val = val.strip()
    if val.lower() in {"true", "false"}:
        return val.lower() == "true"
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def load_params(path: str | Path = Path(__file__).resolve().parent / "params.yaml"):
    """YAML 形式 (key: value) を読み込み環境変数に設定."""
    p = Path(path)
    if not p.exists():
        return {}
    params: dict[str, object] = {}
    current_key = None
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("-"):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val:
                params[key] = _parse_value(val)
                current_key = None
            else:
                params[key] = []
                current_key = key
        elif line.startswith("-") and current_key:
            params[current_key].append(_parse_value(line[1:].strip()))
    for k, v in params.items():
        if isinstance(v, list):
            os.environ[k] = ",".join(str(item) for item in v)
        else:
            os.environ[k] = str(v)
    return params
