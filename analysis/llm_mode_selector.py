from __future__ import annotations

"""LLM を用いたモード選択ラッパー (互換用)."""

from types import SimpleNamespace
from typing import Any, Dict

from .regime_selector_llm import select_mode


def select_mode_llm(features: Dict[str, Any]) -> str:
    """LLM を利用してモードを選択する互換ラッパー."""
    snapshot = SimpleNamespace(**features)
    mode, _ = select_mode(snapshot)
    return mode


__all__ = ["select_mode_llm"]
