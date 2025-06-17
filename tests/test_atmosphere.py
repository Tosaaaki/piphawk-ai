from analysis.atmosphere.feature_extractor import AtmosphereFeatures
from analysis.atmosphere.regime_classifier import RegimeClassifier
from analysis.atmosphere.score_calculator import AtmosphereScore
from signals.atmosphere_signal import generate_signal


def _sample_candles():
    return [
        {"open": 100, "close": 101, "volume": 10},
        {"open": 101, "close": 102, "volume": 12},
        {"open": 102, "close": 101, "volume": 8},
    ]


def test_feature_extractor():
    feats = AtmosphereFeatures(_sample_candles()).extract()
    assert "vwap_bias" in feats
    assert "volume_delta" in feats


def test_score_and_classify():
    feats = AtmosphereFeatures(_sample_candles()).extract()
    score = AtmosphereScore().calc(feats)
    tag = RegimeClassifier().classify(score)
    assert tag in {"Risk-On", "Risk-Off", "Neutral"}


def test_generate_signal():
    feats = AtmosphereFeatures(_sample_candles()).extract()
    score = AtmosphereScore().calc(feats)
    sig = generate_signal(score, rsi=20)
    assert sig in {None, "long", "short"}
