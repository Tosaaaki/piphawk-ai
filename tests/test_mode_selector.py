import importlib

from analysis import llm_mode_selector as lm
from analysis import mode_preclassifier as mp
from backend.utils import openai_client


def test_classify_regime_boundary():
    feat = {"adx": 35, "atr_percentile": 50, "atr_pct": 20}
    assert mp.classify_regime(feat) == "trend"
    feat["adx"] = 19
    assert mp.classify_regime(feat) == "range"
    feat["adx"] = 27
    assert mp.classify_regime(feat) == "gray"
    feat["atr_percentile"] = 5
    assert mp.classify_regime(feat) == "no_trade"


def test_llm_fallback(monkeypatch):
    monkeypatch.setattr(lm, "ask_openai", lambda *a, **k: {"mode": "trend_follow"})
    assert lm.select_mode_llm({}) == "trend_follow"

    def raise_err(*_a, **_k):
        raise RuntimeError("fail")

    monkeypatch.setattr(lm, "ask_openai", raise_err)
    assert lm.select_mode_llm({}) == "no_trade"
