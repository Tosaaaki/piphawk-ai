from __future__ import annotations

"""Order manager factory."""

from backend.utils import env_loader

from backend.orders.order_manager import OrderManager
from backend.orders.mock_order_manager import MockOrderManager


def get_order_manager() -> OrderManager | MockOrderManager:
    """環境変数 ``PAPER_MODE`` が真ならモックを返す."""
    if env_loader.get_env("PAPER_MODE", "false").lower() == "true":
        return MockOrderManager()
    return OrderManager()

__all__ = ["get_order_manager", "OrderManager", "MockOrderManager"]
