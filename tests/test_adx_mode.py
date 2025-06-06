import importlib
import os


def _load_module():
    import sys, types

    pandas_stub = types.ModuleType("pandas")
    pandas_stub.Series = lambda data: data
    sys.modules.setdefault("pandas", pandas_stub)

    boll_stub = types.ModuleType("indicators.bollinger")
    def multi_bollinger(data, window=20, num_std=2):
        res = {}
        for tf, prices in data.items():
            last = prices[-1]
            res[tf] = {"middle": last, "upper": last + 1, "lower": last - 1}
        return res
    boll_stub.multi_bollinger = multi_bollinger
    sys.modules["indicators.bollinger"] = boll_stub

    scalp_stub = types.ModuleType("signals.scalp_strategy")
    scalp_stub.analyze_environment_m1 = lambda closes: "trend"
    scalp_stub.should_enter_trade_s10 = lambda direction, closes, bands: "long"
    sys.modules["signals.scalp_strategy"] = scalp_stub

    import signals.adx_strategy as mod
    importlib.reload(mod)
    return mod


def test_choose_strategy():
    os.environ.pop("ADX_SCALP_MIN", None)
    os.environ.pop("ADX_TREND_MIN", None)
    mod = _load_module()
    assert mod.ADX_SCALP_MIN == 20.0
    assert mod.ADX_TREND_MIN == 30.0
    assert mod.choose_strategy(15) == "none"
    assert mod.choose_strategy(25) == "scalp"
    assert mod.choose_strategy(35) == "trend_follow"


def test_env_override():
    os.environ["ADX_SCALP_MIN"] = "25"
    os.environ["ADX_TREND_MIN"] = "40"
    mod = _load_module()
    assert mod.ADX_SCALP_MIN == 25.0
    assert mod.ADX_TREND_MIN == 40.0
    assert mod.choose_strategy(20) == "none"
    assert mod.choose_strategy(30) == "scalp"
    assert mod.choose_strategy(45) == "trend_follow"
    os.environ.pop("ADX_SCALP_MIN")
    os.environ.pop("ADX_TREND_MIN")


def test_entry_signal_scalp():
    mod = _load_module()
    adx = mod.ADX_SCALP_MIN + 1
    closes_m1 = [1] * 20 + [2]
    closes_s10 = list(range(20)) + [50]
    side = mod.entry_signal(adx, closes_m1, closes_s10)
    assert side == "long"


def test_entry_signal_trend():
    mod = _load_module()
    adx = mod.ADX_TREND_MIN + 10
    closes_m1 = [1, 2, 3]
    closes_s10 = [1, 2, 3]
    side = mod.entry_signal(adx, closes_m1, closes_s10)
    assert side == "long"


