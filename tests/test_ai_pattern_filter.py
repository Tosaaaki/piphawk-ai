import numpy as np
import pytest

from ai.cnn_pattern import infer

pytest.importorskip("fastapi")
pytest.skip("skip pattern filter on limited environment", allow_module_level=True)

from signals.ai_pattern_filter import decide_entry_side, pass_pattern_filter


def _dummy_candles() -> list[dict]:
    return [
        {"o": 1.0, "h": 1.1, "l": 0.9, "c": 1.05},
        {"o": 1.05, "h": 1.15, "l": 0.95, "c": 1.1},
        {"o": 1.1, "h": 1.2, "l": 1.0, "c": 1.15},
        {"o": 1.15, "h": 1.25, "l": 1.05, "c": 1.2},
    ]


def test_pattern_filter_false(monkeypatch):
    def fake(img: np.ndarray) -> dict[str, float]:
        return {"pattern": 0.1}

    monkeypatch.setattr(infer, "predict", fake)
    ok, prob = pass_pattern_filter(_dummy_candles())
    assert not ok
    assert prob == 0.1


def test_pattern_filter_true(monkeypatch):
    def fake(img: np.ndarray) -> dict[str, float]:
        return {"pattern": 0.7}

    monkeypatch.setattr(infer, "predict", fake)
    ok, prob = pass_pattern_filter(_dummy_candles())
    assert ok
    assert prob > 0.65


def test_decide_entry_side_long(monkeypatch):
    def fake(img: np.ndarray) -> dict[str, float]:
        return {"pattern": 0.8}

    monkeypatch.setattr(infer, "predict", fake)
    side, prob = decide_entry_side(_dummy_candles())
    assert side == "long"
    assert prob == 0.8


def test_decide_entry_side_short(monkeypatch):
    def fake(img: np.ndarray) -> dict[str, float]:
        return {"pattern": 0.2}

    monkeypatch.setattr(infer, "predict", fake)
    side, prob = decide_entry_side(_dummy_candles())
    assert side == "short"
    assert prob == 0.2


def test_decide_entry_side_low_prob(monkeypatch):

    def fake(img: np.ndarray) -> dict[str, float]:
        return {"pattern": 0.55}

    monkeypatch.setattr(infer, "predict", fake)
    side, prob = decide_entry_side(_dummy_candles())

    assert side == "long"


