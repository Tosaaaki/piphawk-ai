"""Compatibility wrappers for AI utilities."""

from .local_model import USE_LOCAL_MODEL, ask_model, ask_model_async
from .macro_analyzer import MacroAnalyzer

__all__ = ["ask_model", "ask_model_async", "USE_LOCAL_MODEL", "MacroAnalyzer"]
