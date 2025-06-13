"""Entry-related helpers for JobRunner."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.utils import env_loader
from backend.strategy.openai_analysis import get_market_condition, get_trade_plan, should_convert_limit_to_market
from backend.utils.ai_parse import parse_trade_plan
from backend.strategy.risk_manager import calc_lot_size
from backend.utils.oanda_client import get_pending_entry_order

__all__ = ["manage_pending_limits"]

def manage_pending_limits(
    runner: Any,
    instrument: str,
    indicators: dict,
    candles: list,
    tick_data: dict,
) -> None:
    """Cancel or renew pending LIMIT orders."""
    MAX_LIMIT_RETRY = int(env_loader.get_env("MAX_LIMIT_RETRY", "3"))
    pend = get_pending_entry_order(instrument)
    if not pend:
        for key, info in list(runner._pending_limits.items()):
            if info.get("instrument") == instrument:
                runner._pending_limits.pop(key, None)
        return

    local_info = None
    for key, info in runner._pending_limits.items():
        if info.get("order_id") == pend.get("order_id"):
            local_info = info | {"key": key}
            break

    order_mgr = runner.order_mgr

    if local_info:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        price = (
            float(tick_data["prices"][0]["bids"][0]["price"])
            if local_info.get("side") == "long"
            else float(tick_data["prices"][0]["asks"][0]["price"])
        )
        limit_price = float(local_info.get("limit_price", price))
        diff_pips = abs(price - limit_price) / pip_size

        atr_series = indicators.get("atr")
        if atr_series is not None and len(atr_series):
            atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            atr_pips = float(atr_val) / pip_size
        else:
            atr_pips = 0.0

        threshold_ratio = float(env_loader.get_env("LIMIT_THRESHOLD_ATR_RATIO", "0.3"))
        adx_series = indicators.get("adx")
        adx_val = adx_series.iloc[-1] if adx_series is not None and len(adx_series) else 0.0

        rsi_series = indicators.get("rsi")
        rsi_val = rsi_series.iloc[-1] if rsi_series is not None and len(rsi_series) else None

        ema_slope_series = indicators.get("ema_slope")
        ema_slope_val = (
            ema_slope_series.iloc[-1]
            if ema_slope_series is not None and len(ema_slope_series)
            else None
        )

        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        bb_width_pips = None
        if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            bb_width_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size

        if atr_pips and diff_pips >= atr_pips * threshold_ratio and adx_val >= 25:
            ctx = {
                "diff_pips": diff_pips,
                "atr_pips": atr_pips,
                "adx": adx_val,
                "rsi": rsi_val,
                "ema_slope": ema_slope_val,
                "bb_width_pips": bb_width_pips,
                "side": local_info.get("side"),
            }
            try:
                allow = should_convert_limit_to_market(ctx)
            except Exception as exc:
                runner.logger.warning(f"AI check failed: {exc}")
                allow = False

            if allow:
                try:
                    runner.logger.info(
                        f"Switching LIMIT {pend['order_id']} to market (diff {diff_pips:.1f} pips)"
                    )
                    order_mgr.cancel_order(pend["order_id"])
                    try:
                        candles_dict = {"M5": candles}
                        indicators_multi = {"M5": indicators}
                        plan = get_trade_plan(
                            tick_data,
                            indicators_multi or {},
                            candles_dict or {},
                            patterns=runner.PATTERN_NAMES,
                            detected_patterns=runner.patterns_by_tf,
                            trade_mode=runner.trade_mode,
                            mode_reason=runner.mode_reason,
                        )
                        plan = parse_trade_plan(plan)
                        risk = plan.get("risk", {})
                        ai_raw = json.dumps(plan, ensure_ascii=False)
                    except Exception as exc:
                        runner.logger.warning(f"get_trade_plan failed: {exc}")
                        risk = {}
                        ai_raw = None

                    try:
                        cond_ind = runner._get_cond_indicators()
                        ctx = {
                            "indicators": {
                                k: float(val.iloc[-1]) if hasattr(val, "iloc") and val.iloc[-1] is not None else float(val) if val is not None else None
                                for k, val in cond_ind.items()
                            },
                            "indicators_h1": {
                                k: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None else float(v) if v is not None else None
                                for k, v in (runner.indicators_H1 or {}).items()
                            },
                            "indicators_h4": {
                                k: float(v.iloc[-1]) if hasattr(v, "iloc") and v.iloc[-1] is not None else float(v) if v is not None else None
                                for k, v in (runner.indicators_H4 or {}).items()
                            },
                        }
                        market_cond = get_market_condition(ctx, {})
                    except Exception as exc:
                        runner.logger.warning(f"get_market_condition failed: {exc}")
                        market_cond = None

                    params = {
                        "instrument": instrument,
                        "side": local_info.get("side"),
                        "tp_pips": risk.get("tp_pips"),
                        "sl_pips": risk.get("sl_pips"),
                        "mode": "market",
                        "limit_price": None,
                        "market_cond": market_cond,
                        "ai_response": ai_raw,
                    }
                    sl_val = params.get("sl_pips") or float(env_loader.get_env("INIT_SL_PIPS", "20"))
                    risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
                    pip_val = float(env_loader.get_env("PIP_VALUE_JPY", "100"))
                    lot = calc_lot_size(
                        runner.account_balance,
                        risk_pct,
                        float(sl_val),
                        pip_val,
                        risk_engine=runner.risk_mgr,
                    )
                    result = order_mgr.enter_trade(
                        side=local_info.get("side"),
                        lot_size=lot if lot > 0 else 0.0,
                        market_data=tick_data,
                        strategy_params=params,
                    )
                except Exception as exc:
                    runner.logger.warning(f"Failed to convert to market order: {exc}")
                else:
                    if result:
                        runner._pending_limits.pop(local_info["key"], None)
                return

    age = time.time() - pend["ts"]
    if age < runner.max_limit_age_sec:
        return

    try:
        runner.logger.info(f"Stale LIMIT order {pend['order_id']} ({age:.0f}s) \u2192 cancelling")
        order_mgr.cancel_order(pend["order_id"])
    except Exception as exc:
        runner.logger.warning(f"Failed to cancel LIMIT order: {exc}")
        return

    retry_count = 0
    for key, info in list(runner._pending_limits.items()):
        if info.get("order_id") == pend["order_id"]:
            retry_count = info.get("retry_count", 0)
            runner._pending_limits.pop(key, None)

    if retry_count >= MAX_LIMIT_RETRY:
        runner.logger.info("LIMIT retry count exceeded \u2013 not placing new order.")
        return

    try:
        candles_dict = {"M5": candles}
        indicators_multi = {"M5": indicators}
        plan = get_trade_plan(
            tick_data,
            indicators_multi or {},
            candles_dict or {},
            patterns=runner.PATTERN_NAMES,
            detected_patterns=runner.patterns_by_tf,
            trade_mode=runner.trade_mode,
            mode_reason=runner.mode_reason,
        )
        plan = parse_trade_plan(plan)
    except Exception as exc:
        runner.logger.warning(f"get_trade_plan failed: {exc}")
        return

    entry = plan.get("entry", {})
    risk = plan.get("risk", {})
    side = entry.get("side", "no").lower()
    if side not in ("long", "short") or entry.get("mode") != "limit":
        runner.logger.info("AI does not propose renewing the LIMIT order.")
        return

    limit_price = entry.get("limit_price")
    if limit_price is None:
        runner.logger.info("AI proposed LIMIT without price \u2013 skipping renewal.")
        return

    entry_uuid = str(uuid.uuid4())[:8]
    params = {
        "instrument": instrument,
        "side": side,
        "tp_pips": risk.get("tp_pips"),
        "sl_pips": risk.get("sl_pips"),
        "mode": "limit",
        "limit_price": limit_price,
        "entry_uuid": entry_uuid,
        "valid_for_sec": int(entry.get("valid_for_sec", runner.max_limit_age_sec)),
        "risk": risk,
    }
    sl_val = params.get("sl_pips") or float(env_loader.get_env("INIT_SL_PIPS", "20"))
    risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
    pip_val = float(env_loader.get_env("PIP_VALUE_JPY", "100"))
    lot = calc_lot_size(
        runner.account_balance,
        risk_pct,
        float(sl_val),
        pip_val,
        risk_engine=runner.risk_mgr,
    )
    result = order_mgr.enter_trade(
        side=side,
        lot_size=lot if lot > 0 else 0.0,
        market_data=tick_data,
        strategy_params=params,
    )
    if result:
        runner._pending_limits[entry_uuid] = {
            "instrument": instrument,
            "order_id": result.get("order_id"),
            "ts": int(datetime.now(timezone.utc).timestamp()),
            "limit_price": limit_price,
            "side": side,
            "retry_count": retry_count + 1,
        }
        runner.logger.info(f"Renewed LIMIT order {result.get('order_id')}")
