import pytest

from piphawk_ai.vote_arch.ai_entry_plan import EntryPlan
from piphawk_ai.vote_arch.ai_strategy_selector import select_strategy
from piphawk_ai.vote_arch.entry_buffer import PlanBuffer
from piphawk_ai.vote_arch.regime_detector import MarketMetrics, rule_based_regime


def test_select_strategy_majority(monkeypatch):
    calls = [
        {"trade_mode": "scalp_momentum", "prob": 0.4},
        {"trade_mode": "trend_follow", "prob": 0.6},
        {"trade_mode": "trend_follow", "prob": 0.7},
    ]

    def fake_ask(prompt: str, system_prompt: str, model: str, temperature: float, response_format: dict, n: int):
        return [calls.pop(0) for _ in range(n)]
    monkeypatch.setattr("piphawk_ai.vote_arch.ai_strategy_selector.ask_openai", fake_ask)
    mode, ok = select_strategy("foo")
    assert mode == "trend_follow"
    assert ok is True


def test_select_strategy_prob_fallback(monkeypatch):
    calls = [
        {"trade_mode": "scalp_momentum", "prob": 0.4},
        {"trade_mode": "trend_follow", "prob": 0.3},
        {"trade_mode": "scalp_reversion", "prob": 0.8},
    ]

    def fake_ask(prompt: str, system_prompt: str, model: str, temperature: float, response_format: dict, n: int):
        return [calls.pop(0) for _ in range(n)]

    monkeypatch.setattr("piphawk_ai.vote_arch.ai_strategy_selector.ask_openai", fake_ask)
    mode, ok = select_strategy("foo")
    assert ok is False
    assert mode == "scalp_reversion"


def test_plan_buffer_average():
    buf = PlanBuffer()
    buf.append(EntryPlan(side="long", tp=10, sl=5, lot=1))
    buf.append(EntryPlan(side="long", tp=12, sl=5, lot=1))
    buf.append(EntryPlan(side="long", tp=14, sl=5, lot=1))
    avg = buf.average()
    assert avg is not None
    assert avg.tp == pytest.approx(12)
    assert avg.sl == 5
    assert avg.side == "long"


def test_rule_based_regime():
    metrics = MarketMetrics(adx_m5=35, ema_fast=1.2, ema_slow=1.0, bb_width_m5=0.1)
    assert rule_based_regime(metrics) == "trend"
    metrics = MarketMetrics(adx_m5=15, ema_fast=1.0, ema_slow=1.0, bb_width_m5=0.03)
    assert rule_based_regime(metrics) == "range"
    metrics = MarketMetrics(adx_m5=25, ema_fast=0.9, ema_slow=1.0, bb_width_m5=0.2)
    assert rule_based_regime(metrics) == "vol_spike"
