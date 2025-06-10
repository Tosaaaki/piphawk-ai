"""Scalp trade management."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.orders.order_manager import OrderManager, get_pip_size
from backend.orders.position_manager import get_open_positions

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "scalp.yml"
try:
    _CONFIG = yaml.safe_load(_CONFIG_PATH.read_text())
except Exception:  # pragma: no cover - config optional
    _CONFIG = {}

SCALP_UNIT_SIZE = int(_CONFIG.get("unit_size", 1000))
SCALP_TP_PIPS = float(_CONFIG.get("tp_pips", 1.5))
SCALP_SL_PIPS = float(_CONFIG.get("sl_pips", 1.0))
MAX_SCALP_HOLD_SECONDS = int(_CONFIG.get("max_hold_sec", 20))

order_mgr = OrderManager()
_open_scalp_trades: dict[str, float] = {}


def enter_scalp_trade(instrument: str, side: str = "long") -> None:
    """Place a market order with attached TP/SL."""
    units = SCALP_UNIT_SIZE if side == "long" else -SCALP_UNIT_SIZE
    res = order_mgr.place_market_with_tp_sl(
        instrument,
        units,
        side,
        tp_pips=SCALP_TP_PIPS,
        sl_pips=SCALP_SL_PIPS,
        comment_json=json.dumps({"mode": "scalp"}),
    )
    trade_id = res.get("lastTransactionID")
    if trade_id:
        _open_scalp_trades[trade_id] = time.time()
    logger.info(f"Enter SCALP {instrument} at {datetime.now(timezone.utc).isoformat()}")


def monitor_scalp_positions() -> None:
    """Close scalp positions that exceed max hold time."""
    positions = get_open_positions() or []
    now = time.time()
    for pos in positions:
        trade_id = pos.get("id") or pos.get("tradeID")
        if not trade_id:
            continue
        start = _open_scalp_trades.get(str(trade_id))
        if start is None:
            continue
        if now - start >= MAX_SCALP_HOLD_SECONDS:
            order_mgr.close_position(pos["instrument"])
            logger.info(
                f"Exit SCALP {pos['instrument']} – timeout hit ({MAX_SCALP_HOLD_SECONDS}s)"
            )
            _open_scalp_trades.pop(str(trade_id), None)
