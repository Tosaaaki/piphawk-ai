import pytest

from piphawk_ai.vote_arch.regime_detector import MarketMetrics
from piphawk_ai.vote_arch.trade_mode_selector import select_mode


def test_select_mode_majority(monkeypatch):
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.ai_strategy_selector.select_strategy",
        lambda _p: ("trend_follow", True),
    )
    metrics = MarketMetrics(adx_m5=30, ema_fast=1.1, ema_slow=1.0, bb_width_m5=0.1)
    assert select_mode("foo", metrics) == "trend_follow"


def test_select_mode_fallback(monkeypatch):
    monkeypatch.setattr(
        "piphawk_ai.vote_arch.ai_strategy_selector.select_strategy",
        lambda _p: ("", False),
    )
    metrics = MarketMetrics(adx_m5=15, ema_fast=1.0, ema_slow=1.0, bb_width_m5=0.04)
    assert select_mode("foo", metrics) == "scalp_momentum"
