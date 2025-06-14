import pytest

from signals.mode_selector_v2 import select_mode


@pytest.mark.parametrize(
    "ctx,expected",
    [
        ({"ema_slope_15m": 0.3, "adx_15m": 35.5, "stddev_pct_15m": 0.3, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "TREND"),
        ({"ema_slope_15m": 0.3, "adx_15m": 34.5, "stddev_pct_15m": 0.3, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "BASE_SCALP"),
        ({"ema_slope_15m": 0.3, "adx_15m": 35.5, "stddev_pct_15m": 0.3, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
        ({"ema_slope_15m": 0.3, "adx_15m": 34.5, "stddev_pct_15m": 0.1, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "BASE_SCALP"),
        ({"ema_slope_15m": 0.3, "adx_15m": 34.5, "stddev_pct_15m": 0.1, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
        ({"ema_slope_15m": 0.1, "adx_15m": 20.0, "stddev_pct_15m": 0.2, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "BASE_SCALP"),
        ({"ema_slope_15m": 0.1, "adx_15m": 20.0, "stddev_pct_15m": 0.31, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "BASE_SCALP"),
        ({"ema_slope_15m": 0.1, "adx_15m": 20.0, "stddev_pct_15m": 0.2, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
        ({"ema_slope_15m": 0.1, "adx_15m": 20.0, "stddev_pct_15m": 0.31, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
        ({"ema_slope_15m": 0.3, "adx_15m": 35.5, "stddev_pct_15m": 0.2, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "TREND"),
        ({"ema_slope_15m": 0.3, "adx_15m": 35.5, "stddev_pct_15m": 0.2, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
        ({"ema_slope_15m": 0.1, "adx_15m": 20.0, "stddev_pct_15m": 0.8, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
        ({"ema_slope_15m": 0.05, "adx_15m": 10.0, "stddev_pct_15m": 0.8, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": False}, "BASE_SCALP"),
        ({"ema_slope_15m": 0.05, "adx_15m": 10.0, "stddev_pct_15m": 0.8, "ema12_15m": 1.0, "ema26_15m": 1.0, "atr_15m": 1.0, "overshoot_flag": True}, "REBOUND_SCALP"),
    ],
)
def test_select_mode_cases(ctx, expected):
    assert select_mode(ctx) == expected
