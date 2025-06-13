import importlib
import textwrap

import pytest


def _load_with_weights(tmp_path, yml_text, monkeypatch):
    cfg = tmp_path / "mode.yml"
    cfg.write_text(textwrap.dedent(yml_text))
    monkeypatch.setenv("MODE_CONFIG", str(cfg))
    import signals.composite_mode as cm
    import signals.mode_params as mp
    importlib.reload(mp)
    return importlib.reload(cm)


def test_weight_application(monkeypatch, tmp_path):
    yml = """
    weights:
      adx_m5: 2
      atr_pct_m5: 1
      ema_slope_base: 1
    """
    monkeypatch.setenv("MODE_ADX_MIN", "30")
    monkeypatch.setenv("MODE_ADX_STRONG", "30")
    monkeypatch.setenv("MODE_DI_DIFF_MIN", "100")
    monkeypatch.setenv("MODE_EMA_SLOPE_MIN", "100")
    monkeypatch.setenv("MODE_EMA_DIFF_MIN", "100")
    monkeypatch.setenv("MODE_VOL_MA_MIN", "1000")
    monkeypatch.setenv("MODE_ATR_PIPS_MIN", "100")
    monkeypatch.setenv("MODE_BONUS_START_JST", "0")
    monkeypatch.setenv("MODE_BONUS_END_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_START_JST", "0")
    monkeypatch.setenv("MODE_PENALTY_END_JST", "0")
    cm = _load_with_weights(tmp_path, yml, monkeypatch)

    inds = {
        "atr": [50],
        "adx": [35],
        "plus_di": [55],
        "minus_di": [20],
        "ema_slope": [0.0],
        "volume": [0, 0, 0, 0, 0],
    }
    _mode, score, _reasons = cm.decide_trade_mode_detail(inds)
    assert score == pytest.approx(0.375)
