from __future__ import annotations

"""Order manager factory."""

import os

from backend.orders.order_manager import OrderManager
from backend.orders.mock_order_manager import MockOrderManager


def get_order_manager() -> OrderManager | MockOrderManager:
    """環境変数 ``PAPER_MODE`` が真ならモックを返す."""
    if os.getenv("PAPER_MODE", "false").lower() == "true":
        return MockOrderManager()
    return OrderManager()

__all__ = ["get_order_manager", "OrderManager", "MockOrderManager"]
