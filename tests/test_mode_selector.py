from analysis import mode_detector as md
from analysis import mode_preclassifier as mp


def test_classify_regime_boundary():
    feat = {"adx": 35, "atr_percentile": 50, "atr_pct": 20}
    assert mp.classify_regime(feat) == "trend"
    feat["adx"] = 19
    assert mp.classify_regime(feat) == "range"
    feat["adx"] = 27
    assert mp.classify_regime(feat) == "gray"
    feat["atr_percentile"] = 5
    assert mp.classify_regime(feat) == "no_trade"


def test_detect_mode():
    features = {"adx": 35, "atr_percentile": 50, "atr_pct": 20}
    assert md.detect_mode_simple(features) == "trend_follow"
    features["adx"] = 19
    assert md.detect_mode_simple(features) == "scalp_momentum"
    features["atr_percentile"] = 5
    assert md.detect_mode_simple(features) == "no_trade"
