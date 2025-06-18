import os
import types

os.environ.setdefault("OPENAI_API_KEY", "dummy")

from signals import scalping_signal, trend_signal


class DummyPredictor:
    def predict(self, _features: dict) -> dict:
        return {"prob_long": 0.7, "prob_short": 0.2, "prob_flat": 0.1}


def test_scalping_signal(monkeypatch):
    monkeypatch.setattr(scalping_signal, "_predictor", DummyPredictor())
    res = scalping_signal.make_signal({"pair": "USD_JPY", "spread": 0.0001, "atr": 0.03})
    assert res in ("BUY", "SELL")


def test_trend_signal(monkeypatch):
    monkeypatch.setattr(trend_signal, "_predictor", DummyPredictor())
    res = trend_signal.recheck({"mode": "trend"})
    assert set(res.keys()) == {"prob_long", "prob_short", "prob_flat"}

