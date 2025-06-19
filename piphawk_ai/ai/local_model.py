"""Compatibility wrapper for :mod:`ai.local_model`."""

from ai.local_model import USE_LOCAL_MODEL, ask_model, ask_model_async

__all__ = ["ask_model", "ask_model_async", "USE_LOCAL_MODEL"]
