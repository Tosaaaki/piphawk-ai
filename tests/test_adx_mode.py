import importlib
import os
import sys
import types


def _reload_module():
    import signals.adx_strategy as mod
    return importlib.reload(mod)


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
    adx = 45
    closes_m1 = [1, 2, 3]
    closes_s10 = [1, 2, 3]
    side = mod.entry_signal(adx, closes_m1, closes_s10, closes_m1)
    assert side == "long"
    os.environ.pop("ADX_SCALP_MIN")
    os.environ.pop("ADX_TREND_MIN")


def test_determine_trade_mode(monkeypatch):
    os.environ["ADX_SCALP_MIN"] = "20"
    os.environ["ADX_TREND_MIN"] = "40"
    mod = _reload_module()

    monkeypatch.setattr(mod, "analyze_environment_tf", lambda closes, tf: "trend")
    assert (
        mod.determine_trade_mode(45, [1, 2, 3], [1, 2, 3], scalp_tf="M1", trend_tf="M5")
        == "trend_follow"
    )

    monkeypatch.setattr(mod, "analyze_environment_tf", lambda closes, tf: "range")
    assert (
        mod.determine_trade_mode(45, [1, 2, 3], [1, 2, 3], scalp_tf="M1", trend_tf="M5")
        == "scalp"
    )

    assert (
        mod.determine_trade_mode(15, [1, 2], scalp_tf="M1", trend_tf="M5") == "none"
    )

    assert (
        mod.determine_trade_mode(25, [1, 2], scalp_tf="M1", trend_tf="M5") == "scalp"
    )

    os.environ.pop("ADX_SCALP_MIN")
    os.environ.pop("ADX_TREND_MIN")
