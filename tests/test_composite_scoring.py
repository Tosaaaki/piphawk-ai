import importlib
import os
import pytest


def _reload_module():
    import signals.composite_mode as cm
    return importlib.reload(cm)


def test_mode_scores_trend(monkeypatch):
    monkeypatch.setenv("MODE_ADX_MIN", "25")
    monkeypatch.setenv("MODE_ADX_STRONG", "40")
    monkeypatch.setenv("MODE_DI_DIFF_MIN", "10")
    monkeypatch.setenv("MODE_DI_DIFF_STRONG", "25")
    monkeypatch.setenv("MODE_EMA_SLOPE_MIN", "0.1")
    monkeypatch.setenv("MODE_EMA_SLOPE_STRONG", "0.3")
    monkeypatch.setenv("MODE_VOL_MA_MIN", "80")
    monkeypatch.setenv("MODE_VOL_RATIO_MIN", "1")
    monkeypatch.setenv("MODE_VOL_RATIO_STRONG", "2")
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "5")
    monkeypatch.setenv("MODE_BONUS_START_JST", "0")
    monkeypatch.setenv("MODE_BONUS_END_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_START_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_END_JST", "0")
    cm = _reload_module()
    inds = {
        "atr": [10.0],
        "adx": [45],
        "plus_di": [50],
        "minus_di": [10],
        "ema_slope": [0.4],
        "volume": [200, 200, 200, 200, 200],
    }
    mode, score, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "strong_trend"
    assert score == pytest.approx(5 / 5.5, abs=1e-6)


def test_mode_scores_scalp(monkeypatch):
    monkeypatch.setenv("MODE_ADX_MIN", "25")
    monkeypatch.setenv("MODE_DI_DIFF_MIN", "10")
    monkeypatch.setenv("MODE_EMA_SLOPE_MIN", "0.1")
    monkeypatch.setenv("MODE_VOL_MA_MIN", "80")
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "5")
    monkeypatch.setenv("MODE_BONUS_START_JST", "0")
    monkeypatch.setenv("MODE_BONUS_END_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_START_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_END_JST", "0")
    cm = _reload_module()
    inds = {
        "atr": [3.0],
        "adx": [20],
        "plus_di": [21],
        "minus_di": [20],
        "ema_slope": [0.05],
        "volume": [60, 60, 60, 60, 60],
    }
    mode, score, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "flat"
    assert score == 0.0


def test_mode_scores_strong_trend(monkeypatch):
    monkeypatch.setenv("MODE_ADX_MIN", "25")
    monkeypatch.setenv("MODE_ADX_STRONG", "40")
    monkeypatch.setenv("MODE_DI_DIFF_MIN", "10")
    monkeypatch.setenv("MODE_DI_DIFF_STRONG", "25")
    monkeypatch.setenv("MODE_EMA_SLOPE_MIN", "0.1")
    monkeypatch.setenv("MODE_EMA_SLOPE_STRONG", "0.3")
    monkeypatch.setenv("MODE_VOL_MA_MIN", "80")
    monkeypatch.setenv("MODE_VOL_RATIO_MIN", "1")
    monkeypatch.setenv("MODE_VOL_RATIO_STRONG", "2")
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "5")
    monkeypatch.setenv("MODE_STRONG_TREND_THRESH", "0.9")
    monkeypatch.setenv("MODE_BONUS_START_JST", "0")
    monkeypatch.setenv("MODE_BONUS_END_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_START_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_END_JST", "0")
    cm = _reload_module()
    inds = {
        "atr": [10.0],
        "adx": [50],
        "plus_di": [55],
        "minus_di": [5],
        "ema_slope": [0.35],
        "ema14": [1.0, 2.0],
        "ema50": [0.5, 0.4],
        "volume": [200, 200, 200, 200, 200],
    }
    mode, score, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "strong_trend"
    assert score == pytest.approx(1.0, abs=1e-6)
