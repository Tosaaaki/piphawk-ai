"""Range からトレンドへの移行を検知するモジュール."""

from __future__ import annotations

from typing import Dict, Any
from collections import deque

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
        low_window: int = 20,
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
        self.cross_wait = 0
        self.prev_di_plus: float | None = None
        self.prev_di_minus: float | None = None
        self.lows: deque[float] = deque(maxlen=low_window)
        self.low_n: float | None = None
        self.atr_ratio: float | None = None

    def update(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """Tick データを処理して状態遷移を返す."""
        adx, delta_adx = self.adx.update(tick)
        bw_ratio = self.bbwidth.update(tick)
        atr_ratio = self.atr.update(tick)
        outside = self.keltner.close_outside(tick)

        di_p = self.adx.last_di_plus
        di_m = self.adx.last_di_minus
        if di_p is not None and di_m is not None:
            if (
                self.prev_di_plus is not None
                and self.prev_di_minus is not None
                and self.prev_di_minus <= self.prev_di_plus
                and di_m > di_p
            ):
                self.cross_wait = 2
            self.prev_di_plus = di_p
            self.prev_di_minus = di_m

        if self.cross_wait > 0:
            if delta_adx > 0:
                self.cross_wait -= 1
            trend_confirm = False
        else:
            trend_confirm = adx > self.adx_threshold and delta_adx > self.adx_slope

        volatility_break = bw_ratio > self.bw_mult and atr_ratio > self.atr_mult
        direction_ok = outside

        if volatility_break and trend_confirm and direction_ok:
            self.state = "TREND"
            return {"transition": True, "direction": self.adx.direction()}

        self.state = "RANGE"
        return {"transition": False}

    def breakout_entry(self, price: Dict[str, Any]) -> Dict[str, str] | None:
        """Breakout entry 判定を行う."""
        close = float(price.get("close", price.get("c", 0)))
        low = float(price.get("low", price.get("l", 0)))

        prev_low_n = min(self.lows) if self.lows else None
        self.lows.append(low)
        self.low_n = min(self.lows)

        adx_val, _ = self.adx.update(price)
        self.atr_ratio = self.atr.update(price)

        if (
            prev_low_n is not None
            and close < prev_low_n
            and adx_val > 22
            and self.atr_ratio > 1.3
        ):
            return {"side": "short", "type": "breakout"}
        return None


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
