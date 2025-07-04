"""Namespace package for piphawk AI."""
import importlib
import sys
from pkgutil import extend_path

_submodules = [
    "backend",
    "analysis",
    "ai",
    "signals",
    "indicators",
    "monitoring",
    "risk",
    "strategies",
    "policy",
    "regime",
    "core",
    "runner",
    "models",
    "training",
]
__path__ = extend_path(__path__, __name__)

for _name in _submodules:
    try:
        module = importlib.import_module(_name)
        sys.modules[f"piphawk_ai.{_name}"] = module
    except Exception:
        # 依存パッケージが欠けている環境でも読み込みを継続する
        pass
