from __future__ import annotations

"""学習済みクラスタリングモデルを用いたレジーム推定ヘルパー."""

from typing import Any
import pickle
from pathlib import Path

import numpy as np

from regime import RegimeFeatureExtractor


class ClusterRegime:
    """保存済みモデルと特徴量抽出器でレジーム推定を行うクラス."""

    def __init__(self, model_path: str, extractor: RegimeFeatureExtractor | None = None) -> None:
        self.model_path = Path(model_path)
        self.extractor = extractor or RegimeFeatureExtractor()
        with self.model_path.open("rb") as f:
            self.model = pickle.load(f)
        self.current: int | None = None

    def update(self, tick: dict[str, Any]) -> dict[str, Any]:
        """tick データを処理してレジーム判定を返す."""
        feat = self.extractor.update(tick).reshape(1, -1)
        label = int(self.model.predict(feat)[0])
        transition = label != self.current
        self.current = label
        return {"regime_id": label, "transition": transition}

    def predict_one(self, x: Any) -> int:
        arr = np.asarray(x).reshape(1, -1)
        return int(self.model.predict(arr)[0])

__all__ = ["ClusterRegime"]
