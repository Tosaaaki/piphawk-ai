from __future__ import annotations

"""Order split and trailing-stop helpers."""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List

from backend.indicators.atr import calculate_atr
from backend.logs.update_oanda_trades import fetch_trade_details
from backend.orders.order_manager import OrderManager
from backend.utils import env_loader
from piphawk_ai.tech_arch.market_context import MarketContext
from piphawk_ai.vote_arch.ai_entry_plan import EntryPlan

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """Simple container for order information."""

    order_id: str
    trade_id: str | None


_SPLIT_TABLE: dict[str, tuple[float, float]] = {
    "trend_follow": (0.7, 0.3),
    "scalp_momentum": (0.5, 0.5),
}


def _parse_time(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def create_split_orders(mode: str, plan: EntryPlan) -> List[Order]:
    """Place two child orders sharing the same position_id."""

    pair = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    ratio = _SPLIT_TABLE.get(mode, (0.7, 0.3))
    pos_id = uuid.uuid4().hex[:8]
    order_mgr = OrderManager()

    results: list[Order] = []
    for r in ratio:
        units = int(plan.lot * r * 1000)
        if plan.side == "short":
            units = -units
        comment = json.dumps({"position_id": pos_id})
        res = order_mgr.place_market_with_tp_sl(
            pair,
            units,
            plan.side,
            plan.tp,
            plan.sl,
            comment_json=comment,
        )
        order_id = res.get("orderFillTransaction", {}).get("id", "")
        trade_id = res.get("orderFillTransaction", {}).get("tradeOpened", {}).get("tradeID")
        results.append(Order(order_id, trade_id))
    return results


def update_trailing_sl(order_id: str, ctx: MarketContext):
    """Update stop loss based on the Chandelier Exit formula."""

    info = fetch_trade_details(order_id) or {}
    trade = info.get("trade", {})
    instrument = trade.get("instrument")
    if not instrument:
        return None
    side = "long" if float(trade.get("currentUnits", 0)) > 0 else "short"
    entry_time = _parse_time(trade.get("openTime", ""))
    if entry_time is None:
        return None
    highs = []
    lows = []
    for c in ctx.candles:
        t = _parse_time(c.get("time"))
        if t is None or t < entry_time:
            continue
        try:
            highs.append(float(c["mid"]["h"]))
            lows.append(float(c["mid"]["l"]))
        except Exception:
            continue
    if not highs or not lows:
        return None
    hh = max(highs)
    ll = min(lows)
    high = [float(c["mid"]["h"]) for c in ctx.candles][-15:]
    low = [float(c["mid"]["l"]) for c in ctx.candles][-15:]
    close = [float(c["mid"]["c"]) for c in ctx.candles][-15:]
    try:
        atr = calculate_atr(high, low, close)
        atr_val = float(atr.iloc[-1]) if hasattr(atr, "iloc") else float(atr[-1])
    except Exception:
        return None
    price = hh - atr_val * 2 if side == "long" else ll + atr_val * 2
    current_sl = None
    try:
        current_sl = float(trade.get("stopLossOrder", {}).get("price"))
    except Exception:
        current_sl = None
    if current_sl is not None:
        if side == "long" and price <= current_sl:
            return None
        if side == "short" and price >= current_sl:
            return None
    return OrderManager().update_trade_sl(order_id, instrument, price)
