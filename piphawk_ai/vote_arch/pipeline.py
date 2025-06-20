from __future__ import annotations

"""Orchestration pipeline for the majority-vote trading architecture."""

from dataclasses import dataclass
from typing import Optional

from analysis.atmosphere.market_air_sensor import MarketSnapshot, air_index
from backend.utils import env_loader

from .ai_entry_plan import EntryPlan, generate_plan
from .entry_buffer import PlanBuffer
from .regime_detector import MarketMetrics, rule_based_regime
from .trade_mode_selector import select_mode

FORCE_ENTER = env_loader.get_env("FORCE_ENTER", "false").lower() == "true"



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
    pair: str | None = None,
    timeframe: str = "M5",
    spread: float = 0.0,
    atr: float | None = None,
    force_enter: bool = False,
) -> PipelineResult:
    """Run the full majority-vote pipeline and return result."""

    pair = pair or env_loader.get_env("DEFAULT_PAIR", "USD_JPY")

    regime = rule_based_regime(metrics)
    air = air_index(snapshot)

    prompt = f"Regime: {regime}\nAir: {air:.2f}"
    mode = select_mode(prompt, metrics)

    plan = None
    for _ in range(3):
        plan = generate_plan(f"trade_mode: {mode}")
        if plan:
            break
    if not plan:
        plan = EntryPlan(side="long", tp=10, sl=5, lot=1)

    if buffer is not None:
        buffer.append(plan)
        avg_plan = buffer.average()
        if avg_plan:
            plan = avg_plan

    # Post-filter は廃止されたため常に True とする
    passed = True
    # FORCE_ENTER が true の場合はフィルタ結果を無視して必ず発注
    if FORCE_ENTER:
        return PipelineResult(plan, mode=mode, regime=regime, passed=True)
    return PipelineResult(plan if passed else None, mode=mode, regime=regime, passed=passed)


__all__ = ["PipelineResult", "run_cycle"]
