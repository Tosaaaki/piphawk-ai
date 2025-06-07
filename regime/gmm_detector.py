from __future__ import annotations

"""Gaussian Mixture Model によるレジーム認識クラス."""

from typing import Any

import numpy as np
from sklearn.mixture import GaussianMixture


class GMMRegimeDetector:
    """単純な GMM ベースのレジーム検出器."""

    def __init__(self, n_components: int = 3, random_state: int | None = None) -> None:
        self.model = GaussianMixture(n_components=n_components, random_state=random_state)

    def fit(self, features: np.ndarray) -> None:
        """特徴量行列でモデルを学習."""
        self.model.fit(features)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """レジームラベルを返す."""
        return self.model.predict(features)

    def predict_one(self, x: Any) -> int:
        """単一サンプルのラベルを返すヘルパー."""
        arr = np.asarray(x).reshape(1, -1)
        return int(self.predict(arr)[0])

__all__ = ["GMMRegimeDetector"]
