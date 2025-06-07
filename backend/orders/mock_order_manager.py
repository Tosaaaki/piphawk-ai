"""Paper trading mock order manager."""
from __future__ import annotations

from typing import Any


class MockOrderManager:
    """本番APIを呼ばずに結果を返すモック."""

    def place_market_order(self, instrument: str, units: int, comment_json: str | None = None) -> dict:
        return {"instrument": instrument, "units": units, "comment": comment_json, "mock": True}

    def place_limit_order(self, *args: Any, **kwargs: Any) -> dict:
        return {"mock": True}

    def cancel_order(self, order_id: str) -> dict:
        return {"mock": True, "order_id": order_id}

    def modify_order_price(self, *args: Any, **kwargs: Any) -> dict:
        return {"mock": True}
