import importlib
import sys
import types

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas may be missing
    stub = types.ModuleType("pandas")
    stub.Series = list
    sys.modules["pandas"] = stub
    pd = stub


def _base_indicators():
    return {
        "rsi": pd.Series([50, 50]),
        "atr": pd.Series([1.0, 1.0]),
        "ema_fast": pd.Series([1.0, 1.0]),
        "ema_slow": pd.Series([1.0, 1.0]),
        "bb_lower": pd.Series([100.0, 100.0]),
        "bb_upper": pd.Series([120.0, 120.0]),
        "bb_middle": pd.Series([110.0, 110.0]),
        "adx": pd.Series([30, 30]),
        "plus_di": pd.Series([21, 22]),
        "minus_di": pd.Series([20, 19]),
    }


def test_overshoot_window(monkeypatch):
    monkeypatch.setenv("OVERSHOOT_WINDOW_CANDLES", "2")
    monkeypatch.setenv("OVERSHOOT_MAX_PIPS", "5")
    monkeypatch.setenv("OVERSHOOT_ATR_MULT", "2")
    monkeypatch.setenv("OVERSHOOT_BASE_MULT", "2")
    monkeypatch.setenv("OVERSHOOT_MAX_MULT", "2")
    monkeypatch.setenv("OVERSHOOT_RECOVERY_RATE", "0")
    monkeypatch.setenv("PIP_SIZE", "1.0")
    monkeypatch.setenv("BAND_WIDTH_THRESH_PIPS", "0")
    monkeypatch.setenv("HIGHER_TF_ENABLED", "false")
    sys.modules.setdefault("requests", types.ModuleType("requests"))
    sys.modules.setdefault("numpy", types.ModuleType("numpy"))

    import backend.strategy.signal_filter as sf

    importlib.reload(sf)

    sf.update_overshoot_window(110, 100)
    sf.update_overshoot_window(111, 109)
    ctx = {}
    result = sf.pass_entry_filter(_base_indicators(), price=110.0, mode="trend_follow", context=ctx)
    assert result is True
    assert ctx.get("overshoot_flag") is True

    sf.update_overshoot_window(111, 109)
    ctx2 = {}
    result = sf.pass_entry_filter(_base_indicators(), price=110.0, mode="trend_follow", context=ctx2)
    assert result is True
