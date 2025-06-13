from __future__ import annotations

"""Utility functions for environment variable management."""

import os
from pathlib import Path
from typing import Iterable, Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # ランタイムに dotenv がなくても動作させる
    def load_dotenv(*_args, **_kwargs) -> None:
        pass

_BASE_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_FILES = [
    _BASE_DIR.parent / ".env",
    _BASE_DIR / "config" / "settings.env",
    _BASE_DIR / "config" / "secret.env",
]

# Automatically load default env files if they exist
for _file in _DEFAULT_FILES:
    if _file.exists():
        load_dotenv(_file, override=False)


def load_env(paths: Iterable[str | Path], *, override: bool = True) -> None:
    """Load additional environment files."""
    for p in paths:
        path = Path(p)
        if path.exists():
            load_dotenv(path, override=override)


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return the value of an environment variable."""
    val = os.getenv(key)
    if isinstance(val, str):
        # 行末のコメントや余分な空白を除去する
        val = val.split("#", 1)[0].strip()
        if not val:
            return default
    if val is None:
        return default
    return val
