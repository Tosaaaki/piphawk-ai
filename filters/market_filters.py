from __future__ import annotations

"""市場状態の簡易フィルター."""

from datetime import datetime, timedelta, timezone

from backend.utils import env_loader


def _in_trade_hours(ts: datetime | None = None) -> bool:
    """取引可能時間かを判定する."""
    ts = (ts or datetime.now(timezone.utc)).astimezone(timezone(timedelta(hours=9)))
    start = float(env_loader.get_env("TRADE_START_H", "7"))
    end = float(env_loader.get_env("TRADE_END_H", "23"))
    current = ts.hour + ts.minute / 60.0
    if start < end:
        return start <= current < end
    return current >= start or current < end


def is_tradeable(pair: str, timeframe: str, spread: float, atr: float | None = None) -> bool:
    """Check if market conditions allow trading."""

    # 日本語コメント: スプレッドとボラティリティをピップスで比較する

    pip_size = 0.01 if pair.endswith("_JPY") else 0.0001
    max_spread = float(env_loader.get_env("MAX_SPREAD_PIPS", "2"))
    if spread / pip_size > max_spread:
        return False

    if atr is not None:
        min_atr = float(env_loader.get_env("MIN_ATR_PIPS", "1"))
        if atr / pip_size < min_atr:
            return False

    return _in_trade_hours()

