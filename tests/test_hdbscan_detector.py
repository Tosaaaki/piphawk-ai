import numpy as np
import pytest

try:
    import hdbscan  # noqa: F401
except Exception:  # pragma: no cover - skip if not available
    pytest.skip("hdbscan not available", allow_module_level=True)

from regime.hdbscan_detector import HDBSCANRegimeDetector


def test_hdbscan_regime_detector():
    X = np.array([[0.0], [0.1], [0.2], [3.0], [3.1], [3.2]])
    detector = HDBSCANRegimeDetector(min_cluster_size=2)
    detector.fit(X)
    labels = detector.predict(X)
    assert set(labels) == {0, 1}
    single = detector.predict_one([0.05])
    assert single in {0, 1}
