import importlib
import pandas as pd


def test_dynamic_overshoot(monkeypatch):
    monkeypatch.setenv("OVERSHOOT_ATR_MULT", "1.0")
    monkeypatch.setenv("OVERSHOOT_DYNAMIC_COEFF", "0.5")
    monkeypatch.setenv("BAND_WIDTH_THRESH_PIPS", "100")
    monkeypatch.setenv("PIP_SIZE", "0.01")
    monkeypatch.setenv("HIGHER_TF_ENABLED", "false")
    import backend.strategy.signal_filter as sf
    importlib.reload(sf)

    indicators = {
        "rsi": pd.Series([50, 50]),
        "atr": pd.Series([0.5, 0.5]),
        "ema_fast": pd.Series([1.0, 1.0]),
        "ema_slow": pd.Series([1.0, 1.0]),
        "bb_lower": pd.Series([99.0, 99.0]),
        "bb_upper": pd.Series([101.0, 101.0]),
        "bb_middle": pd.Series([100.0, 100.0]),
        "adx": pd.Series([30, 30]),
        "plus_di": pd.Series([21, 22]),
        "minus_di": pd.Series([20, 19]),
    }

    result = sf.pass_entry_filter(indicators, price=98.0, mode="trend_follow")
    assert result is False
