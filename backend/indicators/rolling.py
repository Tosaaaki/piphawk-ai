"""Rolling indicator utilities using deque for efficiency."""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict


class RollingATR:
    """ATR をローリングで計算して EMA 比を返すクラス."""

    def __init__(self, length: int = 14) -> None:
        self.length = length
        self.tr_values: Deque[float] = deque(maxlen=length)
        self.prev_close: float | None = None
        self.ema: float | None = None
        self.alpha = 2 / (length + 1)

    def update(self, tick: Dict[str, Any]) -> float:
        """高値・安値・終値を含む tick データで更新する."""
        high = float(tick["high"])
        low = float(tick["low"])
        close = float(tick["close"])
        if self.prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        self.tr_values.append(tr)
        self.prev_close = close
        atr = sum(self.tr_values) / len(self.tr_values)
        self.ema = atr if self.ema is None else self.ema + self.alpha * (atr - self.ema)
        if self.ema:
            return atr / self.ema
        return 1.0


class RollingADX:
    """ADX とその増減を算出するローリングクラス."""

    def __init__(self, length: int = 14) -> None:
        self.length = length
        self.prev_high: float | None = None
        self.prev_low: float | None = None
        self.prev_close: float | None = None
        self.tr_values: Deque[float] = deque(maxlen=length)
        self.plus_dm: Deque[float] = deque(maxlen=length)
        self.minus_dm: Deque[float] = deque(maxlen=length)
        self.adx: float | None = None
        self.prev_adx: float | None = None
        self.last_di_plus: float | None = None
        self.last_di_minus: float | None = None

    def update(self, tick: Dict[str, Any]) -> tuple[float, float]:
        high = float(tick["high"])
        low = float(tick["low"])
        close = float(tick["close"])
        if self.prev_high is None:
            self.prev_high = high
            self.prev_low = low
            self.prev_close = close
            return 0.0, 0.0
        tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        up_move = high - self.prev_high
        down_move = self.prev_low - low
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0
        self.tr_values.append(tr)
        self.plus_dm.append(plus_dm)
        self.minus_dm.append(minus_dm)
        self.prev_high = high
        self.prev_low = low
        self.prev_close = close
        if len(self.tr_values) < self.length:
            self.last_di_plus = None
            self.last_di_minus = None
            return 0.0, 0.0
        atr = sum(self.tr_values) / len(self.tr_values)
        di_plus = 100 * (sum(self.plus_dm) / len(self.plus_dm)) / atr if atr else 0.0
        di_minus = 100 * (sum(self.minus_dm) / len(self.minus_dm)) / atr if atr else 0.0
        self.last_di_plus = di_plus
        self.last_di_minus = di_minus
        denom = di_plus + di_minus
        dx = 100 * abs(di_plus - di_minus) / denom if denom else 0.0
        if self.adx is None:
            self.adx = dx
        else:
            self.adx = (self.adx * (self.length - 1) + dx) / self.length
        delta = self.adx - self.prev_adx if self.prev_adx is not None else 0.0
        self.prev_adx = self.adx
        return self.adx, delta

    def direction(self) -> str:
        plus = sum(self.plus_dm) / len(self.plus_dm) if self.plus_dm else 0.0
        minus = sum(self.minus_dm) / len(self.minus_dm) if self.minus_dm else 0.0
        return "up" if plus >= minus else "down"


class RollingBBWidth:
    """BB 幅の変化率を計算するローリングクラス."""

    def __init__(self, window: int = 20, avg_len: int = 50) -> None:
        self.window = window
        self.avg_len = avg_len
        self.prices: Deque[float] = deque(maxlen=window)
        self.widths: Deque[float] = deque(maxlen=avg_len)

    def update(self, tick_or_price: Any) -> float:
        price = float(tick_or_price["close"] if isinstance(tick_or_price, dict) else tick_or_price)
        self.prices.append(price)
        if len(self.prices) < self.window:
            width = 0.0
        else:
            mean = sum(self.prices) / len(self.prices)
            var = sum((p - mean) ** 2 for p in self.prices) / len(self.prices)
            std = var ** 0.5
            width = 4 * std
        self.widths.append(width)
        avg = sum(self.widths) / len(self.widths) if self.widths else 0.0
        return width / avg if avg else 0.0


class RollingKeltner:
    """Keltner Channel をローリングで計算するクラス."""

    def __init__(self, window: int = 20, atr_mult: float = 1.5) -> None:
        self.window = window
        self.atr_mult = atr_mult
        self.alpha = 2 / (window + 1)
        self.prev_close: float | None = None
        self.ema: float | None = None
        self.tr_values: Deque[float] = deque(maxlen=window)

    def update(self, tick: Dict[str, Any]) -> Dict[str, float]:
        high = float(tick["high"])
        low = float(tick["low"])
        close = float(tick["close"])
        typical = (high + low + close) / 3
        self.ema = typical if self.ema is None else self.ema + self.alpha * (typical - self.ema)
        if self.prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - self.prev_close), abs(low - self.prev_close))
        self.tr_values.append(tr)
        self.prev_close = close
        atr = sum(self.tr_values) / len(self.tr_values)
        upper = self.ema + self.atr_mult * atr
        lower = self.ema - self.atr_mult * atr
        return {"middle": self.ema, "upper": upper, "lower": lower}

    def close_outside(self, tick: Dict[str, Any]) -> bool:
        if self.ema is None:
            bands = {"upper": float("inf"), "lower": float("-inf")}
        else:
            atr = sum(self.tr_values) / len(self.tr_values) if self.tr_values else 0.0
            bands = {
                "upper": self.ema + self.atr_mult * atr,
                "lower": self.ema - self.atr_mult * atr,
            }
        close = float(tick["close"])
        outside = close > bands["upper"] or close < bands["lower"]
        self.update(tick)
        return outside


class RollingVolumeRatio:
    """出来高比率を返す簡易クラス."""

    def __init__(self, window: int = 20) -> None:
        self.window = window
        self.volumes: Deque[float] = deque(maxlen=window)

    def update(self, tick: Dict[str, Any]) -> float:
        """``volume`` 値から現在値/平均値を計算する."""
        vol = float(tick.get("volume", 0.0))
        self.volumes.append(vol)
        avg = sum(self.volumes) / len(self.volumes) if self.volumes else 0.0
        return (vol / avg) if avg else 1.0


__all__ = [
    "RollingATR",
    "RollingADX",
    "RollingBBWidth",
    "RollingKeltner",
    "RollingVolumeRatio",
]
