"""Range からトレンドへの移行を検知するモジュール."""

from __future__ import annotations

from typing import Dict, Any

from backend.indicators.rolling import (
    RollingATR,
    RollingADX,
    RollingBBWidth,
    RollingKeltner,
)


class RegimeDetector:
    """3 レイヤー判定でレンジ離れを検知するクラス."""

    def __init__(
        self,
        len_fast: int = 14,
        bw_mult: float = 1.5,
        atr_mult: float = 1.3,
        adx_threshold: float = 25.0,
        adx_slope: float = 0.5,
        bb_window: int = 20,
        keltner_window: int = 20,
    ) -> None:
        self.adx = RollingADX(len_fast)
        self.bbwidth = RollingBBWidth(window=bb_window)
        self.atr = RollingATR(len_fast)
        self.keltner = RollingKeltner(window=keltner_window)
        self.state = "RANGE"
        self.bw_mult = bw_mult
        self.atr_mult = atr_mult
        self.adx_threshold = adx_threshold
        self.adx_slope = adx_slope

    def update(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """Tick データを処理して状態遷移を返す."""
        adx, delta_adx = self.adx.update(tick)
        bw_ratio = self.bbwidth.update(tick)
        atr_ratio = self.atr.update(tick)
        outside = self.keltner.close_outside(tick)

        volatility_break = bw_ratio > self.bw_mult and atr_ratio > self.atr_mult
        trend_confirm = adx > self.adx_threshold and delta_adx > self.adx_slope
        direction_ok = outside

        if volatility_break and trend_confirm and direction_ok:
            self.state = "TREND"
            return {"transition": True, "direction": self.adx.direction()}

        self.state = "RANGE"
        return {"transition": False}


class ATRBoostDetector:
    """ATR 比率が閾値を超えたか判定するクラス."""

    def __init__(self, length: int = 14, threshold: float = 1.2) -> None:
        self.atr = RollingATR(length)
        self.threshold = threshold

    def update(self, tick: Dict[str, Any]) -> bool:
        """ATR / ATR EMA が閾値を上回ると True."""
        ratio = self.atr.update(tick)
        return ratio > self.threshold


__all__ = ["RegimeDetector", "ATRBoostDetector"]
