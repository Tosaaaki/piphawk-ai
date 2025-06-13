import numpy as np

from regime.gmm_detector import GMMRegimeDetector


def test_gmm_regime_detector():
    X = np.array([[0.0], [0.1], [0.2], [3.0], [3.1], [3.2]])
    detector = GMMRegimeDetector(n_components=2, random_state=42)
    detector.fit(X)
    labels = detector.predict(X)
    assert set(labels) == {0, 1}
    single = detector.predict_one([0.05])
    assert single in {0, 1}

