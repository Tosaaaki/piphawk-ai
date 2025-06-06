import importlib
import os
import sys
import types


def _reload_module():
    import signals.adx_strategy as mod
    return importlib.reload(mod)


def _reload_composite():
    import signals.composite_mode as cm
    return importlib.reload(cm)


def test_choose_strategy_default():
    os.environ.pop("ADX_SCALP_MIN", None)
    os.environ.pop("ADX_TREND_MIN", None)
    mod = _reload_module()
    assert mod.ADX_SCALP_MIN == 20.0
    assert mod.ADX_TREND_MIN == 30.0
    assert mod.choose_strategy(15) == "none"
    assert mod.choose_strategy(25) == "scalp"
    assert mod.choose_strategy(35) == "trend_follow"


def test_choose_strategy_env_override():
    os.environ["ADX_SCALP_MIN"] = "10"
    os.environ["ADX_TREND_MIN"] = "25"
    sys.modules.setdefault("pandas", types.ModuleType("pandas"))
    mod = _reload_module()
    assert mod.ADX_SCALP_MIN == 10.0
    assert mod.ADX_TREND_MIN == 25.0
    assert mod.choose_strategy(9) == "none"
    assert mod.choose_strategy(15) == "scalp"
    assert mod.choose_strategy(30) == "trend_follow"
    os.environ.pop("ADX_SCALP_MIN")
    os.environ.pop("ADX_TREND_MIN")


def test_entry_signal_scalp():
    os.environ["ADX_SCALP_MIN"] = "20"
    os.environ["ADX_TREND_MIN"] = "40"
    mod = _reload_module()
    adx = 25
    closes_m1 = [1] * 20 + [2]
    closes_s10 = list(range(20)) + [50]
    side = mod.entry_signal(adx, closes_m1, closes_s10, closes_m1)
    assert side == "long"
    os.environ.pop("ADX_SCALP_MIN")
    os.environ.pop("ADX_TREND_MIN")


def test_entry_signal_trend():
    os.environ["ADX_SCALP_MIN"] = "20"
    os.environ["ADX_TREND_MIN"] = "40"
    mod = _reload_module()
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    mp.setattr(mod, "analyze_environment_tf", lambda closes, tf: "trend")
    adx = 45
    closes_m1 = [1, 2, 3]
    closes_s10 = [1, 2, 3]
    side = mod.entry_signal(adx, closes_m1, closes_s10, closes_m1)
    assert side == "long"
    mp.undo()
    os.environ.pop("ADX_SCALP_MIN")
    os.environ.pop("ADX_TREND_MIN")


def test_decide_trade_mode_matrix(monkeypatch):
    monkeypatch.setenv("ATR_HIGH_RATIO", "1.3")
    monkeypatch.setenv("ATR_LOW_RATIO", "0.8")
    monkeypatch.setenv("ADX_TREND_THR", "25")
    monkeypatch.setenv("ADX_FLAT_THR", "15")
    cm = _reload_composite()
    inds = {
        "atr": [0.05],
        "bb_upper": [101.0],
        "bb_lower": [100.0],
        "ema_slope": [0.2],
        "macd_hist": [0.3],
        "adx": [30],
        "volume": [60, 70, 80, 90, 100],
    }
    assert cm.decide_trade_mode(inds) == "trend_follow"


def test_decide_trade_mode_scalp(monkeypatch):
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "6")
    monkeypatch.setenv("MODE_BBWIDTH_PIPS_MIN", "4")
    monkeypatch.setenv("MODE_EMA_SLOPE_MIN", "0.5")
    monkeypatch.setenv("MODE_ADX_MIN", "50")
    monkeypatch.setenv("MODE_VOL_MA_MIN", "100")
    cm = _reload_composite()
    inds = {
        "atr": [0.03],
        "bb_upper": [100.03],
        "bb_lower": [100.0],
        "ema_slope": [0.1],
        "macd_hist": [0.05],
        "adx": [20],
        "volume": [20, 30, 40, 50, 60],
    }
    assert cm.decide_trade_mode(inds) == "scalp"


def test_decide_trade_mode_high_atr_low_adx(monkeypatch):
    monkeypatch.setenv("HIGH_ATR_PIPS", "3")
    monkeypatch.setenv("LOW_ADX_THRESH", "20")
    cm = _reload_composite()
    inds = {
        "atr": [0.03],
        "bb_upper": [101.0],
        "bb_lower": [100.0],
        "ema_slope": [0.0],
        "macd_hist": [0.0],
        "adx": [10],
        "volume": [50, 50, 50, 50, 50],
    }
    assert cm.decide_trade_mode(inds) == "scalp"
    assert cm.decide_trade_mode_matrix(1.5, 1.0, 10) == "scalp_range"
    assert cm.decide_trade_mode_matrix(1.5, 1.0, 30) == "scalp_momentum"
    assert cm.decide_trade_mode_matrix(0.7, 1.0, 30) == "trend_follow"
    assert cm.decide_trade_mode_matrix(1.0, 1.0, 20) == "flat"
