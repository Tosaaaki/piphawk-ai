"""Namespace package for piphawk AI."""
from pkgutil import extend_path
import importlib
import sys

_submodules = [
    "backend",
    "analysis",
    "ai",
    "signals",
    "indicators",
    "monitoring",
    "risk",
    "strategies",
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
    except ModuleNotFoundError:
        pass
