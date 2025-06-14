import importlib

from signals import mode_selector


def test_select_mode_trend():
    ctx = {"ema_slope_15m": 0.3, "adx_15m": 40, "overshoot_flag": 0}
    importlib.reload(mode_selector)
    assert mode_selector.select_mode(ctx) == "TREND"


def test_select_mode_rebound():
    ctx = {"ema_slope_15m": 0.1, "adx_15m": 10, "overshoot_flag": 1}
    assert mode_selector.select_mode(ctx) == "REBOUND_SCALP"


def test_select_mode_base():
    ctx = {"ema_slope_15m": 0.05, "adx_15m": 10, "overshoot_flag": 0}
    assert mode_selector.select_mode(ctx) == "BASE_SCALP"
