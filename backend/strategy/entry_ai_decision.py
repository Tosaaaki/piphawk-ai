"""
DEPRECATED MODULE
-----------------
Entry‑decision logic has been consolidated into
`backend.strategy.openai_analysis.get_entry_decision`.

This stub exists only to preserve backward compatibility for
legacy imports:

    from backend.strategy.entry_ai_decision import get_entry_decision

It immediately re‑exports the current implementation.
"""

from backend.strategy.openai_analysis import get_entry_decision  # noqa: F401

__all__ = ["get_entry_decision"]
