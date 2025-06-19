from __future__ import annotations

"""セッション判定と超低ボラチェック用フィルター."""

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.utils import env_loader


def is_quiet_hours(now: datetime | None = None) -> bool:
    """JST 03-06時を静寂時間帯として判定する."""
    jst = (now or datetime.utcnow()).astimezone(timezone(timedelta(hours=9)))
    return 3 <= jst.hour < 6


def apply_filters(atr: float, bb_width_pct: float, *, tradeable: bool = True) -> tuple[bool, dict[str, Any] | None, str | None]:
    """禁止3条件を評価し、regime_hint を返す."""
    if is_quiet_hours():
        return False, None, "session"
    if not tradeable:
        return False, None, "market_closed"
    scalp_min = float(env_loader.get_env("SCALP_ATR_MIN", "0.03"))
    trend_min = float(env_loader.get_env("TREND_ATR_MIN", "0.1"))
    if atr < scalp_min and bb_width_pct < 0.10:
        return False, None, "ultra_low_vol"
    ctx = {"regime_hint": "scalp" if atr < trend_min else "trend"}
    return True, ctx, None
