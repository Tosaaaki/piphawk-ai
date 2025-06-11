"""Scalp trade management."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from backend.utils import env_loader

try:
    from backend.orders.order_manager import OrderManager, get_pip_size
except Exception:  # テストでモックが残っている場合のフォールバック
    class OrderManager:
        pass

    def get_pip_size(instrument: str) -> float:
        return 0.01 if instrument.endswith("_JPY") else 0.0001

import inspect
from backend.orders.position_manager import get_open_positions
from signals.scalp_momentum import exit_if_momentum_loss

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
    """Place a market order with dynamically calculated TP/SL."""

    tp_pips = None
    sl_pips = None
    atr_pips = None
    pip_size = get_pip_size(instrument)
    try:
        from backend.market_data.candle_fetcher import fetch_candles
        from backend.indicators.calculate_indicators import calculate_indicators
        from backend.strategy import openai_scalp_analysis as scalp_ai

        candles = fetch_candles(
            instrument, granularity="M5", count=30, allow_incomplete=True
        )
        indicators = calculate_indicators(candles, pair=instrument)

        plan = scalp_ai.get_scalp_plan(indicators, candles)
        tp_pips = plan.get("tp_pips")
        sl_pips = plan.get("sl_pips")

        atr = indicators.get("atr")
        if atr is not None:
            atr_val = (
                float(atr.iloc[-1]) if hasattr(atr, "iloc") else float(atr[-1])
            )
            atr_pips = atr_val / pip_size
    except Exception as exc:  # pragma: no cover - network/parse failure
        logger.debug("scalp plan/indicator fetch failed: %s", exc)

    if tp_pips is None and atr_pips is not None:
        mult = float(env_loader.get_env("ATR_MULT_TP", "0.8"))
        tp_pips = atr_pips * mult
    if sl_pips is None and atr_pips is not None:
        mult = float(env_loader.get_env("ATR_MULT_SL", "1.1"))
        sl_pips = atr_pips * mult

    if tp_pips is None:
        tp_pips = SCALP_TP_PIPS
    if sl_pips is None:
        sl_pips = SCALP_SL_PIPS

    min_sl = float(env_loader.get_env("MIN_SL_PIPS", "0"))
    dyn_min = 0.0
    if atr_pips is not None:
        mult = float(env_loader.get_env("ATR_SL_MULTIPLIER", "2.0"))
        dyn_min = atr_pips * mult
    sl_pips = max(sl_pips, min_sl, dyn_min)

    units = SCALP_UNIT_SIZE if side == "long" else -SCALP_UNIT_SIZE
    params = {
        "tp_pips": tp_pips,
        "sl_pips": sl_pips,
        "comment_json": json.dumps({"mode": "scalp"}),
    }
    if "price_bound" in inspect.signature(order_mgr.place_market_with_tp_sl).parameters:
        params["price_bound"] = None

    res = order_mgr.place_market_with_tp_sl(
        instrument,
        units,
        side,
        **params,
    )
    trade_id = (
        res.get("orderFillTransaction", {})
        .get("tradeOpened", {})
        .get("tradeID")
    )
    if trade_id:
        _open_scalp_trades[trade_id] = time.time()
        # TP が付いているか確認し、無ければ再設定する
        if hasattr(order_mgr, "get_current_tp"):
            time.sleep(1)
            try:
                current_tp = order_mgr.get_current_tp(trade_id)
            except Exception:
                current_tp = None
            if current_tp is None:
                price = float(res.get("orderFillTransaction", {}).get("price", 0.0))
                tp_price = price + tp_pips * pip_size if side == "long" else price - tp_pips * pip_size
                sl_price = price - sl_pips * pip_size if side == "long" else price + sl_pips * pip_size
                try:
                    order_mgr.adjust_tp_sl(
                        instrument,
                        trade_id,
                        new_tp=tp_price,
                        new_sl=sl_price,
                    )
                    logger.info(f"Reattached TP/SL for trade {trade_id}")
                except Exception as exc:
                    logger.warning(f"TP/SL reattach failed: {exc}")
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
            continue

        # ----- momentum loss check ----------------------------------
        try:
            from backend.market_data.candle_fetcher import fetch_candles
            from backend.indicators.calculate_indicators import calculate_indicators

            candles = fetch_candles(
                pos["instrument"], granularity="M5", count=30, allow_incomplete=True
            )
            indicators = calculate_indicators(candles, pair=pos["instrument"])
        except Exception as exc:  # pragma: no cover - network failure
            logger.debug("indicator fetch failed: %s", exc)
            continue

        try:
            if exit_if_momentum_loss(indicators):
                order_mgr.close_position(pos["instrument"])
                logger.info(
                    f"Exit SCALP {pos['instrument']} – momentum loss"
                )
                _open_scalp_trades.pop(str(trade_id), None)
        except Exception as exc:  # pragma: no cover - safety
            logger.debug("momentum check failed: %s", exc)
