import importlib
import os


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
    monkeypatch.setenv("MODE_EMA_DIFF_MIN", "0.1")
    monkeypatch.setenv("MODE_EMA_DIFF_STRONG", "0.3")
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
    assert score > 0.9

    assert mode == "trend_follow"
    assert score >= 0.8


def test_mode_scores_scalp(monkeypatch):
    monkeypatch.setenv("MODE_ADX_MIN", "25")
    monkeypatch.setenv("MODE_DI_DIFF_MIN", "10")
    monkeypatch.setenv("MODE_EMA_SLOPE_MIN", "0.1")
    monkeypatch.setenv("MODE_VOL_MA_MIN", "80")
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "5")
    monkeypatch.setenv("MODE_EMA_DIFF_MIN", "0.1")
    monkeypatch.setenv("MODE_EMA_DIFF_STRONG", "0.3")
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
    assert mode == "scalp_momentum"
    assert score < 0.5


def test_mode_scores_strong_trend(monkeypatch):
def test_trend_follow_with_large_ema_diff(monkeypatch):

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
    monkeypatch.setenv("MODE_EMA_DIFF_MIN", "0.2")
    monkeypatch.setenv("MODE_EMA_DIFF_STRONG", "0.5")
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "5")
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
        "volume": [200, 200, 200, 200, 200],
    }
    mode, score, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "strong_trend"
    assert score >= 0.9
        "adx": [15],
        "plus_di": [55],
        "minus_di": [5],
        "ema_slope": [0.05],
        "ema14": [100, 101],
        "ema50": [100, 100.2],
        "volume": [200, 200, 200, 200, 200],
    }
    mode, score, _ = cm.decide_trade_mode_detail(inds)
    assert mode == "trend_follow"

