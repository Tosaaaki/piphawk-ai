"""Quick 2-pip scalping loop."""

from __future__ import annotations

import json
import logging
import time

from backend.market_data.tick_fetcher import fetch_tick_data
from backend.market_data.tick_metrics import calc_tick_features
from backend.orders.order_manager import OrderManager, get_pip_size
from backend.orders.position_manager import get_open_positions
from backend.strategy.openai_micro_scalp import get_plan
from backend.utils import env_loader

logger = logging.getLogger(__name__)


def run_loop() -> None:
    """Run micro scalp mode that aims for 2 pips repeatedly."""
    instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    interval = int(env_loader.get_env("QUICK_TP_INTERVAL_SEC", "360"))
    units = int(env_loader.get_env("QUICK_TP_UNITS", "1000"))

    om = OrderManager()

    while True:
        try:
            positions = get_open_positions() or []
            if positions:
                time.sleep(interval)
                continue

            tick = fetch_tick_data(instrument)
            bid = float(tick["prices"][0]["bids"][0]["price"])
            ask = float(tick["prices"][0]["asks"][0]["price"])
            feats = calc_tick_features([{"bid": bid, "ask": ask}])
            plan = get_plan(feats)
            side = plan.get("side")
            if side not in ("long", "short"):
                time.sleep(interval)
                continue

            units_signed = units if side == "long" else -units
            res = om.place_market_with_tp_sl(
                instrument,
                units_signed,
                side,
                tp_pips=2.0,
                sl_pips=0.0,
                comment_json=json.dumps({"mode": "quick_tp"}),
            )

            trade_id = (
                res.get("orderFillTransaction", {})
                .get("tradeOpened", {})
                .get("tradeID")
            )
            if trade_id:
                time.sleep(1)
                current_tp = om.get_current_tp(trade_id)
                if current_tp is None:
                    price = float(res.get("orderFillTransaction", {}).get("price", 0.0))
                    pip = get_pip_size(instrument)
                    tp_price = price + 2.0 * pip if side == "long" else price - 2.0 * pip
                    om.adjust_tp_sl(instrument, trade_id, new_tp=tp_price)
                    logger.info("Reattached TP for trade %s", trade_id)
            logger.info("Entered %s %s for 2 pips TP", side, instrument)
        except Exception as exc:  # pragma: no cover - network or API error
            logger.warning("quick_tp iteration failed: %s", exc)
        time.sleep(interval)

