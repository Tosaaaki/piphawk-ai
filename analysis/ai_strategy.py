"""AI ストラテジー補助モジュール."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from backend.utils import env_loader

try:
    from config import params_loader
    params_loader.load_params()
except Exception:
    pass


def _to_decimal(hm: str) -> float:
    """HH:MM 形式を10進数時間へ変換."""
    h, m = hm.split(":")
    return int(h) + int(m) / 60


def in_no_trade_period(ts: datetime | None = None) -> bool:
    """NO_TRADE の時間帯なら True."""
    ts = ts or datetime.now(timezone.utc) + timedelta(hours=9)
    ranges = env_loader.get_env("NO_TRADE", "")
    current = ts.hour + ts.minute / 60
    for block in ranges.split(','):
        if '-' not in block:
            continue
        start_s, end_s = block.split('-', 1)
        try:
            start = _to_decimal(start_s)
            end = _to_decimal(end_s)
        except Exception:
            continue
        if start < end:
            if start <= current < end:
                return True
        else:
            if current >= start or current < end:
                return True
    return False


def atr_spike(atr_short: float, atr_long: float) -> bool:
    """ATR 比率が閾値を超えたら True."""
    ratio = float(env_loader.get_env("ATR_RATIO", "0"))
    if atr_long == 0:
        return False
    return (atr_short / atr_long) > ratio

__all__ = ["in_no_trade_period", "atr_spike"]
