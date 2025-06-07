"""Strategy base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Strategy(ABC):
    """戦略クラスの基本インターフェース."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def decide_entry(self, context: Dict[str, Any]) -> str | None:
        """コンテキストからエントリー方向を判定."""

    @abstractmethod
    def execute_trade(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        """実際の発注処理を行い結果を返す."""
