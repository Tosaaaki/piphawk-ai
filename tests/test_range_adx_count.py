import importlib
import os


def _reload_composite():
    import signals.composite_mode as cm
    return importlib.reload(cm)


def _base_indicators(adx):
    return {
        "atr": [10.0],
        "adx": [adx],
        "plus_di": [50],
        "minus_di": [10],
        "ema_slope": [0.4],
        "volume": [200, 200, 200, 200, 200],
    }


def test_range_adx_single_dip_no_switch(monkeypatch):
    monkeypatch.setenv("RANGE_ADX_MIN", "20")
    monkeypatch.setenv("RANGE_ADX_COUNT", "3")
    monkeypatch.setenv("MODE_ADX_MIN", "25")
    cm = _reload_composite()

    inds = _base_indicators(15)
    mode, _, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "trend_follow"

    inds = _base_indicators(30)
    mode, _, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "trend_follow"


def test_range_adx_switch_after_threshold(monkeypatch):
    monkeypatch.setenv("RANGE_ADX_MIN", "20")
    monkeypatch.setenv("RANGE_ADX_COUNT", "2")
    monkeypatch.setenv("MODE_ADX_MIN", "25")
    cm = _reload_composite()

    inds = _base_indicators(15)
    mode, _, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "trend_follow"

    inds = _base_indicators(15)
    mode, _, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "scalp_momentum"
