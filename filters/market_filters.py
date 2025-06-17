from __future__ import annotations

"""市場状態の簡易フィルター."""

from datetime import datetime, timedelta, timezone

from backend.utils import env_loader


def _in_trade_hours(ts: datetime | None = None) -> bool:
    """取引可能時間かを判定する."""
    ts = (ts or datetime.utcnow()).astimezone(timezone(timedelta(hours=9)))
    start = int(env_loader.get_env("TRADE_START_H", "7"))
    end = int(env_loader.get_env("TRADE_END_H", "23"))
    if start < end:
        return start <= ts.hour < end
    return ts.hour >= start or ts.hour < end


def is_tradeable(pair: str, timeframe: str, spread: float) -> bool:
    """スプレッドと時間帯が条件を満たすか確認する.

    pair と timeframe は現段階では未使用.
    """
    max_spread = float(env_loader.get_env("MAX_SPREAD", "0.0002"))
    if spread > max_spread:
        return False
    return _in_trade_hours()

