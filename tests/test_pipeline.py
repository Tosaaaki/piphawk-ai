import sys
import types

import pytest

# Stub requests module for isolated testing
sys.modules.setdefault("requests", types.ModuleType("requests"))
openai_stub = types.ModuleType("openai")
openai_stub.OpenAI = object
openai_stub.APIError = Exception
sys.modules.setdefault("openai", openai_stub)
pandas_stub = types.ModuleType("pandas")
pandas_stub.Series = object
pandas_stub.DataFrame = object
sys.modules.setdefault("pandas", pandas_stub)

from analysis.atmosphere.market_air_sensor import MarketSnapshot
from piphawk_ai.vote_arch.ai_entry_plan import EntryPlan
from piphawk_ai.vote_arch.entry_buffer import PlanBuffer
from piphawk_ai.vote_arch.pipeline import PipelineResult, run_cycle
from piphawk_ai.vote_arch.regime_detector import MarketMetrics


def test_run_cycle(monkeypatch):
    def fake_filter(indicators, price=None, **_):
        return True

    monkeypatch.setattr(
        "backend.strategy.signal_filter.pass_entry_filter", fake_filter
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.pass_entry_filter", fake_filter
    )

    def fake_select(prompt: str, n=None):
        return "scalp_momentum", True

    monkeypatch.setattr(
        "piphawk_ai.vote_arch.ai_strategy_selector.select_strategy", fake_select
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.select_strategy", fake_select
    )

    def fake_plan(prompt: str):
        return EntryPlan(side="long", tp=10, sl=5, lot=1)

    monkeypatch.setattr(
        "piphawk_ai.vote_arch.ai_entry_plan.generate_plan", fake_plan
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.generate_plan", fake_plan
    )


    metrics = MarketMetrics(adx_m5=30, ema_fast=1.1, ema_slow=1.0, bb_width_m5=0.1)
    snapshot = MarketSnapshot(atr=0.05, news_score=0.0, oi_bias=0.0)
    result = run_cycle(
        {},
        metrics,
        snapshot,
        PlanBuffer(),
        pair="USD_JPY",
        timeframe="M5",
        spread=0.01,
        atr=0.05,
    )

    assert isinstance(result, PipelineResult)
    assert result.passed is True
    assert result.plan is not None
    assert result.mode == "scalp_momentum"
    assert result.regime == "trend"


def test_run_cycle_filter_block(monkeypatch):
    monkeypatch.setattr(
        "backend.strategy.signal_filter.pass_entry_filter", lambda *a, **k: False
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.pass_entry_filter", lambda *a, **k: False
    )
    metrics = MarketMetrics(0, 0, 0, 0)
    snapshot = MarketSnapshot(0, 0, 0)
    result = run_cycle(
        {},
        metrics,
        snapshot,
        pair="USD_JPY",
        timeframe="M5",
        spread=0.01,
        atr=0.05,
    )
    assert result.passed is False
    assert result.plan is None

