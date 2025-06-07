from regime.features import RegimeFeatureExtractor


def test_volume_ratio_feature():
    extractor = RegimeFeatureExtractor(window=3)
    ticks = [
        {"high": 1, "low": 1, "close": 1, "volume": 2},
        {"high": 1, "low": 1, "close": 1, "volume": 4},
        {"high": 1, "low": 1, "close": 1, "volume": 6},
    ]
    feats = extractor.process_all(ticks)
    assert feats.shape == (3, 4)
    assert abs(feats[-1, 3] - 1.5) < 0.01

