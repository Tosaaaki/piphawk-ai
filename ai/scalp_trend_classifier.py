from __future__ import annotations

"""市場レジームをスキャルかトレンドに分類するクラス."""

from typing import Dict


class MarketRegimeClassifier:
    """シンプルな指標ロジックによるレジーム判定クラス."""

    def __init__(self, scalp_atr_min: float = 0.05, trend_atr_min: float = 0.2) -> None:
        self.scalp_atr_min = scalp_atr_min
        self.trend_atr_min = trend_atr_min

    def classify(self, indicators: Dict[str, float]) -> str:
        """ATR、ADX、MA角度などからレジームを返す."""
        atr = indicators.get("atr", 0.0)
        adx = indicators.get("adx", 0.0)
        ma1 = indicators.get("ma_angle_m1", 0.0)
        ma5 = indicators.get("ma_angle_m5", 0.0)
        bb_ratio = indicators.get("bb_atr_ratio", 0.0)
        scalp_score = 0
        if self.scalp_atr_min <= atr < self.trend_atr_min:
            scalp_score += 1
        if abs(ma1) <= 3 and abs(ma5) <= 3:
            scalp_score += 1
        if adx < 18:
            scalp_score += 1
        if atr and bb_ratio < 1.5:
            scalp_score += 1
        return "scalp" if scalp_score >= 2 else "trend"
