import pytest
from backend.strategy.validators import normalize_probs, risk_autofix
from backend.config.defaults import MIN_ABS_SL_PIPS


def test_normalize_probs_within_range():
    tp, sl = normalize_probs(0.9, 0.6)
    assert tp == pytest.approx(0.6, abs=1e-6)
    assert sl == pytest.approx(0.4, abs=1e-6)
    assert tp + sl == pytest.approx(1.0, abs=1e-6)


def test_normalize_probs_outside_range():
    tp, sl = normalize_probs(0.4, 0.0)
    assert tp == 0.4
    assert sl == 0.0


def test_risk_autofix_defaults():
    r = risk_autofix(None)
    assert r["tp_pips"] == 10.0
    assert r["sl_pips"] >= 6.0 and r["sl_pips"] >= MIN_ABS_SL_PIPS
    assert r["tp_prob"] == pytest.approx(0.6, abs=1e-6)
    assert r["sl_prob"] == pytest.approx(0.4, abs=1e-6)
