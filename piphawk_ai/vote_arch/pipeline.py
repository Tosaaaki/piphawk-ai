from __future__ import annotations

"""Orchestration pipeline for the majority-vote trading architecture."""

from dataclasses import dataclass
from typing import Optional

from backend.strategy.signal_filter import pass_entry_filter

from .ai_entry_plan import EntryPlan, generate_plan
from .ai_strategy_selector import select_strategy
from .entry_buffer import PlanBuffer
from .market_air_sensor import MarketSnapshot, air_index
from .post_filters import final_filter
from .regime_detector import MarketMetrics, rule_based_regime
from .trade_mode_selector import choose_mode


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

    mode = choose_mode(conf_ok, mode_raw, regime, indicators)

    plan = generate_plan(f"trade_mode: {mode}")
    if not plan:
        return PipelineResult(None, mode=mode, regime=regime, passed=False)

    if buffer is not None:
        buffer.append(plan)
        avg_plan = buffer.average()
        if avg_plan:
            plan = avg_plan

    passed = final_filter(plan, indicators)
    return PipelineResult(plan if passed else None, mode=mode, regime=regime, passed=passed)


__all__ = ["PipelineResult", "run_cycle"]
