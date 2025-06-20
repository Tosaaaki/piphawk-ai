from __future__ import annotations

"""セッション判定と超低ボラチェック用フィルター."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.utils import env_loader
from filters.market_filters import _in_trade_hours

# ログ出力用ロガー
log = logging.getLogger(__name__)


def is_quiet_hours(now: datetime | None = None) -> bool:
    """JST 03-06時を静寂時間帯として判定する."""
    jst = (now or datetime.utcnow()).astimezone(timezone(timedelta(hours=9)))
    return 3 <= jst.hour < 6


def apply_filters(
    atr: float,
    bb_width_pct: float,
    spread_pips: float | None = None,
    *,
    tradeable: bool = True,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """禁止3条件を評価し、regime_hint を返す."""
    if is_quiet_hours():
        # 静寂時間帯を検知
        log.info("Filter blocked: session")
        return False, None, "session"
    # 市場が開いているか、取引可能かを判定
    if not _in_trade_hours() or not tradeable:
        log.info("Filter blocked: market_closed")
        return False, None, "market_closed"
    scalp_min = float(env_loader.get_env("SCALP_ATR_MIN", "0.02"))
    trend_min = float(env_loader.get_env("TREND_ATR_MIN", "0.05"))
    max_spread = float(env_loader.get_env("MAX_SPREAD_PIPS", "0"))
    if spread_pips is not None and max_spread > 0 and spread_pips > max_spread:
        log.info("Filter blocked: wide_spread")
        return False, None, "wide_spread"
    if atr < scalp_min and bb_width_pct < 0.10:
        log.info("Filter blocked: ultra_low_vol")
        return False, None, "ultra_low_vol"
    ctx = {"regime_hint": "scalp" if atr < trend_min else "trend"}
    return True, ctx, None
