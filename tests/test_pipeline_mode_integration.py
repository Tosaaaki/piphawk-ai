import pytest

from analysis.atmosphere.market_air_sensor import MarketSnapshot
from piphawk_ai.vote_arch.ai_entry_plan import EntryPlan
from piphawk_ai.vote_arch.entry_buffer import PlanBuffer
from piphawk_ai.vote_arch.pipeline import PipelineResult, run_cycle
from piphawk_ai.vote_arch.regime_detector import MarketMetrics


@pytest.mark.parametrize("mode_raw, conf_ok", [("TREND", True)])
def test_run_cycle_returns_valid_mode(monkeypatch, mode_raw, conf_ok):
    monkeypatch.setattr(
        "backend.strategy.signal_filter.pass_entry_filter", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.pass_entry_filter", lambda *_a, **_k: True
    )

    monkeypatch.setattr(
        "piphawk_ai.vote_arch.ai_strategy_selector.select_strategy", lambda _p: (mode_raw, conf_ok)
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.select_strategy", lambda _p: (mode_raw, conf_ok)
    )

    monkeypatch.setattr(
        "piphawk_ai.vote_arch.ai_entry_plan.generate_plan",
        lambda _p: EntryPlan(side="long", tp=10, sl=5, lot=1),
    )
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.pipeline.generate_plan",
        lambda _p: EntryPlan(side="long", tp=10, sl=5, lot=1),
    )


    metrics = MarketMetrics(adx_m5=30, ema_fast=1.1, ema_slow=1.0, bb_width_m5=0.1)
    snapshot = MarketSnapshot(atr=0.05, news_score=0.0, oi_bias=0.0)

    result = run_cycle({}, metrics, snapshot, PlanBuffer())

    assert isinstance(result, PipelineResult)
    assert result.mode in {"TREND", "BASE_SCALP", "REBOUND_SCALP"}
