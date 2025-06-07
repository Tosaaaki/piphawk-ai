from __future__ import annotations

"""レジーム分類用の特徴量計算ヘルパー."""

from typing import Any, Dict

import numpy as np

from backend.indicators.rolling import (
    RollingATR,
    RollingADX,
    RollingBBWidth,
    RollingVolumeRatio,
)


class RegimeFeatureExtractor:
    """ローリング指標を用いた特徴量抽出クラス."""

    def __init__(self, window: int = 20) -> None:
        self.atr = RollingATR(window)
        self.adx = RollingADX(window)
        self.bbwidth = RollingBBWidth(window=window)
        self.volume = RollingVolumeRatio(window)

    def update(self, tick: Dict[str, Any]) -> np.ndarray:
        """tick データから特徴量を生成する."""
        atr_ratio = self.atr.update(tick)
        adx_val, _ = self.adx.update(tick)
        bw_ratio = self.bbwidth.update(tick)
        vol_ratio = self.volume.update(tick)
        return np.array([atr_ratio, adx_val, bw_ratio, vol_ratio], dtype=float)

    def process_all(self, data: list[Dict[str, Any]]) -> np.ndarray:
        """複数データポイントから特徴量行列を作成する."""
        feats = [self.update(t) for t in data]
        return np.vstack(feats)

__all__ = ["RegimeFeatureExtractor"]
