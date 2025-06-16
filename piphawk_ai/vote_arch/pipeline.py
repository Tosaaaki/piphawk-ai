from __future__ import annotations

"""Orchestration pipeline for the majority-vote trading architecture."""

from dataclasses import dataclass
from typing import Optional

from backend.strategy.signal_filter import pass_entry_filter
from signals.mode_selector_v2 import select_mode

from .ai_entry_plan import EntryPlan, generate_plan
from .ai_strategy_selector import select_strategy
from .entry_buffer import PlanBuffer
from .market_air_sensor import MarketSnapshot, air_index
from .post_filters import final_filter
from .regime_detector import MarketMetrics, rule_based_regime


@dataclass
class PipelineResult:
    """Simple result object for one trading cycle."""

    plan: Optional[EntryPlan]
    mode: str
    regime: str
    passed: bool


def run_cycle(
    indicators: dict,
    metrics: MarketMetrics,
    snapshot: MarketSnapshot,
    buffer: PlanBuffer | None = None,
    *,
    price: float | None = None,
) -> PipelineResult:
    """Run the full majority-vote pipeline and return result."""

    if not pass_entry_filter(indicators, price):
        return PipelineResult(None, mode="", regime="", passed=False)

    regime = rule_based_regime(metrics)
    air = air_index(snapshot)

    prompt = f"Regime: {regime}\nAir: {air:.2f}"
    mode_raw, conf_ok = select_strategy(prompt)

    def _last(v):
        if v is None:
            return 0.0
        try:
            if hasattr(v, "iloc"):
                return float(v.iloc[-1]) if len(v) else 0.0
            if isinstance(v, (list, tuple)):
                return float(v[-1]) if v else 0.0
            return float(v)
        except Exception:
            return 0.0

    ctx = {
        "ema_slope_15m": _last(indicators.get("ema_slope_15m") or indicators.get("ema_slope")),
        "adx_15m": _last(indicators.get("adx_15m") or indicators.get("adx")),
        "stddev_pct_15m": _last(indicators.get("stddev_pct_15m") or indicators.get("stddev_pct")),
        "ema12_15m": _last(indicators.get("ema12_15m") or indicators.get("ema_fast")),
        "ema26_15m": _last(indicators.get("ema26_15m") or indicators.get("ema_slow")),
        "atr_15m": _last(indicators.get("atr_15m") or indicators.get("atr")),
        "overshoot_flag": indicators.get("overshoot_flag", False),
    }
    # LLM提案が高信頼なら優先、そうでなければ数値モード
    mode_llm = mode_raw if conf_ok else ""
    mode_calc = select_mode(ctx)
    mode = mode_llm or mode_calc

    plan = generate_plan(f"trade_mode: {mode}")
    if not plan:
        return PipelineResult(None, mode=mode, regime=regime, passed=False)

    if buffer is not None:
        buffer.append(plan)
        avg_plan = buffer.average()
        if avg_plan:
            plan = avg_plan

    # 最終フィルターの結果に関係なく計画を採用する
    passed = final_filter(plan, indicators)
    return PipelineResult(plan, mode=mode, regime=regime, passed=passed)


__all__ = ["PipelineResult", "run_cycle"]
