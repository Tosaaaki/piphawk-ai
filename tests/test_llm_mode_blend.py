import importlib

import analysis.regime_selector_llm as rsl
import signals.mode_selector_v2 as ms
from analysis.atmosphere.market_air_sensor import MarketSnapshot


def test_llm_blend_base_overrides(monkeypatch):
    monkeypatch.setattr(rsl, "select_mode", lambda *_a, **_k: ("no_trade", {"TREND": 0.1, "BASE_SCALP": 0.9, "REBOUND_SCALP": 0.0}))
    importlib.reload(ms)
    ctx = {
        "ema_slope_15m": 0.3,
        "adx_15m": 45,
        "stddev_pct_15m": 0.2,
        "ema12_15m": 1.0,
        "ema26_15m": 1.0,
        "atr_15m": 1.0,
        "overshoot_flag": False,
    }
    snapshot = MarketSnapshot(0.05, 0.0, 0.0)
    assert ms.select_mode(ctx, snapshot) == "BASE_SCALP"


def test_llm_blend_respects_overshoot(monkeypatch):
    monkeypatch.setattr(rsl, "select_mode", lambda *_a, **_k: ("no_trade", {"TREND": 1.0, "BASE_SCALP": 0.0, "REBOUND_SCALP": 0.0}))
    importlib.reload(ms)
    ctx = {
        "ema_slope_15m": 0.0,
        "adx_15m": 10,
        "stddev_pct_15m": 0.5,
        "ema12_15m": 1.0,
        "ema26_15m": 1.0,
        "atr_15m": 1.0,
        "overshoot_flag": True,
    }
    snapshot = MarketSnapshot(0.05, 0.0, 0.0)
    assert ms.select_mode(ctx, snapshot) == "REBOUND_SCALP"
