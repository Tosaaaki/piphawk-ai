from __future__ import annotations

"""HDBSCAN によるレジーム認識クラス."""

from typing import Any

import numpy as np

try:
    import hdbscan
    from hdbscan import prediction as hdbscan_prediction
except Exception as exc:  # pragma: no cover - optional dependency
    hdbscan = None
    hdbscan_prediction = None


class HDBSCANRegimeDetector:
    """HDBSCAN を用いたレジーム分類器."""

    def __init__(self, min_cluster_size: int = 5) -> None:
        if hdbscan is None:
            raise ImportError("hdbscan library is required for HDBSCANRegimeDetector")
        self.model = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, prediction_data=True)

    def fit(self, features: np.ndarray) -> None:
        """特徴量行列でモデルを学習."""
        self.model.fit(features)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """レジームラベルを返す."""
        if hdbscan_prediction is None:
            raise RuntimeError("hdbscan prediction utilities not available")
        labels, _ = hdbscan_prediction.approximate_predict(self.model, features)
        return labels

    def predict_one(self, x: Any) -> int:
        """単一サンプルのラベルを返すヘルパー."""
        arr = np.asarray(x).reshape(1, -1)
        return int(self.predict(arr)[0])

__all__ = ["HDBSCANRegimeDetector"]
