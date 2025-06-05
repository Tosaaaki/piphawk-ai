from __future__ import annotations

from typing import Sequence, Optional


class DoubleBottomSignal:
    """Detect double-bottom pattern and compute features."""

    def __init__(self, max_separation: int = 10, tolerance: float = 0.001, volume_window: int = 5) -> None:
        self.max_separation = max_separation
        self.tolerance = tolerance
        self.volume_window = volume_window

    def evaluate(self, candles: Sequence[dict]) -> Optional[dict]:
        """Return pattern features or ``None`` when not detected."""
        rows = list(candles)
        if len(rows) < 3:
            return None
        lows: list[float] = []
        highs: list[float] = []
        volumes: list[float | None] = []
        for row in rows:
            mid = row.get("mid", {})
            try:
                lows.append(float(mid.get("l", row.get("l"))))
                highs.append(float(mid.get("h", row.get("h"))))
            except Exception:
                return None
            vol = row.get("volume")
            try:
                volumes.append(float(vol) if vol is not None else None)
            except Exception:
                volumes.append(None)
        i1 = lows.index(min(lows))
        second = None
        for j in range(i1 + 2, min(len(lows), i1 + self.max_separation + 1)):
            if abs(lows[j] - lows[i1]) <= self.tolerance * max(abs(lows[i1]), 1.0):
                second = j
                break
        if second is None:
            return None
        interval = second - i1
        neck = max(highs[i1 + 1:second]) if interval > 1 else highs[i1]
        after = max(highs[second + 1:]) if second + 1 < len(highs) else highs[second]
        neckline_ratio = 0.0
        if neck != 0:
            neckline_ratio = (after - neck) / abs(neck)
        vol_spike = False
        vol = volumes[second]
        if vol is not None and self.volume_window > 0:
            start = max(0, second - self.volume_window)
            sample = [v for v in volumes[start:second] if v is not None]
            if sample:
                avg = sum(sample) / len(sample)
                vol_spike = vol > avg * 1.5
        return {"interval": interval, "neckline_ratio": neckline_ratio, "vol_spike": vol_spike}

class DoubleTopSignal:
    """Detect double-top pattern and compute features."""

    def __init__(self, max_separation: int = 10, tolerance: float = 0.001, volume_window: int = 5) -> None:
        self.max_separation = max_separation
        self.tolerance = tolerance
        self.volume_window = volume_window

    def evaluate(self, candles: Sequence[dict]) -> Optional[dict]:
        """Return pattern features or ``None`` when not detected."""
        rows = list(candles)
        if len(rows) < 3:
            return None
        highs: list[float] = []
        lows: list[float] = []
        volumes: list[float | None] = []
        for row in rows:
            mid = row.get("mid", {})
            try:
                highs.append(float(mid.get("h", row.get("h"))))
                lows.append(float(mid.get("l", row.get("l"))))
            except Exception:
                return None
            vol = row.get("volume")
            try:
                volumes.append(float(vol) if vol is not None else None)
            except Exception:
                volumes.append(None)
        i1 = highs.index(max(highs))
        second = None
        for j in range(i1 + 2, min(len(highs), i1 + self.max_separation + 1)):
            if abs(highs[j] - highs[i1]) <= self.tolerance * max(abs(highs[i1]), 1.0):
                second = j
                break
        if second is None:
            return None
        interval = second - i1
        neck = min(lows[i1 + 1:second]) if interval > 1 else lows[i1]
        after = min(lows[second + 1:]) if second + 1 < len(lows) else lows[second]
        neckline_ratio = 0.0
        if neck != 0:
            neckline_ratio = (neck - after) / abs(neck)
        vol_spike = False
        vol = volumes[second]
        if vol is not None and self.volume_window > 0:
            start = max(0, second - self.volume_window)
            sample = [v for v in volumes[start:second] if v is not None]
            if sample:
                avg = sum(sample) / len(sample)
                vol_spike = vol > avg * 1.5
        return {"interval": interval, "neckline_ratio": neckline_ratio, "vol_spike": vol_spike}

__all__ = ["DoubleBottomSignal", "DoubleTopSignal"]
