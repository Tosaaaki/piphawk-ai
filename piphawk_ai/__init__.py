"""Namespace package for piphawk AI."""
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
    "policy",
    "regime",
    "core",
    "models",
    "training",
]
for _name in _submodules:
    try:
        module = importlib.import_module(_name)
        sys.modules[f"piphawk_ai.{_name}"] = module
    except ModuleNotFoundError:
        pass
