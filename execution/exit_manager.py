from __future__ import annotations

"""Exit management utilities."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from backend.indicators.atr import calculate_atr
from backend.indicators.ema import calculate_ema
from backend.logs.update_oanda_trades import fetch_trade_details
from backend.orders.order_manager import OrderManager
from backend.orders.position_manager import get_open_positions
from backend.utils import env_loader, parse_json_answer, trade_age_seconds
from backend.utils.openai_client import ask_openai

logger = logging.getLogger(__name__)


class ExitManager:
    """Manage exit related checks and AI forecasting."""

    def __init__(self, instrument: str) -> None:
        self.instrument = instrument
        self.order_mgr = OrderManager()
        self._ema_cross_count = 0
        self._bar_count = 0
        self.last_forecast: Dict[str, Any] | None = None

    # --------------------------------------------------------------
    # AI forecast
    # --------------------------------------------------------------
    def llm_exit_forecast(self, max_rev_pips: int) -> Dict[str, Any]:
        """Ask LLM for reversal risk forecast."""
        ctx = {"instrument": self.instrument, "max_rev_pips": max_rev_pips}
        prompt = json.dumps(ctx, ensure_ascii=False)
        system_prompt = (
            "You are an expert FX trader. "
            "Predict whether price will reverse beyond stop-loss. "
            'Reply with JSON {"reverse_gt_sl":bool,"suggest_tp":float}.'
        )
        model = env_loader.get_env("AI_EXIT_MODEL", "gpt-4.1-nano")
        temperature = float(env_loader.get_env("AI_EXIT_TEMPERATURE", "0.0"))
        try:
            raw = ask_openai(
                prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=64,
                temperature=temperature,
            )
        except Exception as exc:  # pragma: no cover - network issues
            logger.warning("llm_exit_forecast failed: %s", exc)
            return {"reverse_gt_sl": False, "suggest_tp": 0.0}
        data, _ = parse_json_answer(raw)
        if not isinstance(data, dict):
            return {"reverse_gt_sl": False, "suggest_tp": 0.0}
        reverse_gt_sl = bool(data.get("reverse_gt_sl"))
        try:
            suggest_tp = float(data.get("suggest_tp", 0.0))
        except (TypeError, ValueError):
            suggest_tp = 0.0
        self.last_forecast = {"reverse_gt_sl": reverse_gt_sl, "suggest_tp": suggest_tp}
        return self.last_forecast

    # --------------------------------------------------------------
    # Monitoring helpers
    # --------------------------------------------------------------
    def on_new_candle(self, candles_m5: list[dict], side: str, max_rev_pips: int) -> None:
        """Update state with a new 5min candle and run checks."""
        if len(candles_m5) < 2:
            return
        self._bar_count += 1
        closes = [float(c["mid"]["c"]) for c in candles_m5]
        ema_series = calculate_ema(closes, period=20)
        prev_close = closes[-2]
        latest_close = closes[-1]
        prev_ema = float(ema_series.iloc[-2])
        latest_ema = float(ema_series.iloc[-1])
        if side == "long" and prev_close >= prev_ema and latest_close < latest_ema:
            self._ema_cross_count += 1
        elif side == "short" and prev_close <= prev_ema and latest_close > latest_ema:
            self._ema_cross_count += 1
        if self._ema_cross_count >= 3:
            try:
                self.order_mgr.close_position(self.instrument, reason="ema_warn")
                logger.info("EMA warn triggered → closing position")
            except Exception as exc:  # pragma: no cover - safety
                logger.warning("close_position failed: %s", exc)
            finally:
                self._ema_cross_count = 0
        if self._bar_count % 3 == 0:
            self.llm_exit_forecast(max_rev_pips)

    def on_tp1_hit(self, max_rev_pips: int) -> None:
        """Handle TP1 fill and check forecast."""
        res = self.llm_exit_forecast(max_rev_pips)
        if res.get("reverse_gt_sl"):
            try:
                self.order_mgr.close_position(self.instrument)
                logger.info("TP1 hit and reversal risk high → closing remaining")
            except Exception as exc:  # pragma: no cover - safety
                logger.warning("close_position failed: %s", exc)


def check_max_hold() -> None:
    """Close positions exceeding MAX_HOLD_HOURS."""
    limit_h = float(env_loader.get_env("MAX_HOLD_HOURS", "6"))
    positions = get_open_positions() or []
    order_mgr = OrderManager()
    now = datetime.now(timezone.utc)
    for pos in positions:
        entry = pos.get("entry_time") or pos.get("openTime")
        age = trade_age_seconds({"entry_time": entry}, now=now)
        if age is None or age < limit_h * 3600:
            continue
        inst = pos.get("instrument")
        if not inst:
            continue
        try:
            pl = float(pos.get("unrealizedPL", 0.0))
        except Exception:
            pl = 0.0
        try:
            order_mgr.close_position(inst)
            logger.info(
                "MAX_HOLD exceeded for %s (%s)", inst, "profit" if pl > 0 else "loss"
            )
        except Exception as exc:  # pragma: no cover - safety
            logger.warning("close_position failed: %s", exc)


def check_stagnation(trade_id: str, candles_m5: list[dict]) -> None:
    """Move SL to break-even when range < ATR*0.2 for 30min."""
    if len(candles_m5) < 6:
        return
    info = fetch_trade_details(trade_id) or {}
    trade = info.get("trade", {})
    instrument = trade.get("instrument")
    if not instrument:
        return
    entry_price = float(trade.get("price", 0.0))
    high = [float(c["mid"]["h"]) for c in candles_m5][-15:]
    low = [float(c["mid"]["l"]) for c in candles_m5][-15:]
    close = [float(c["mid"]["c"]) for c in candles_m5][-15:]
    try:
        atr = calculate_atr(high, low, close)
        atr_val = float(atr.iloc[-1]) if hasattr(atr, "iloc") else float(atr[-1])
    except Exception:
        return
    width_ok = all(
        float(c["mid"]["h"]) - float(c["mid"]["l"]) < atr_val * 0.2
        for c in candles_m5[-6:]
    )
    if width_ok:
        try:
            OrderManager().update_trade_sl(trade_id, instrument, entry_price)
            logger.info("Stagnation detected → SL moved to break-even")
        except Exception as exc:  # pragma: no cover - safety
            logger.warning("update_trade_sl failed: %s", exc)
