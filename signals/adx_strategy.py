from __future__ import annotations

"""ADX値に基づくシンプルなストラテジー切換ユーティリティ."""

from typing import Sequence, Optional

from backend.utils import env_loader

from indicators.bollinger import multi_bollinger
from signals.scalp_strategy import analyze_environment_m1, should_enter_trade_s10


ADX_SCALP_MIN = float(env_loader.get_env("ADX_SCALP_MIN", "20"))
ADX_TREND_MIN = float(env_loader.get_env("ADX_TREND_MIN", "30"))


def choose_strategy(adx_value: float) -> str:
    """ADXの値からモードを判定."""
    if adx_value < ADX_SCALP_MIN:
        return "none"
    if adx_value < ADX_TREND_MIN:
        return "scalp"
    return "trend_follow"


def entry_signal(
    adx_value: float,
    closes_m1: Sequence[float],
    closes_s10: Sequence[float],
) -> Optional[str]:
    """ADXに応じたトレード方向を組織."""
    mode = choose_strategy(adx_value)
    if mode == "scalp":
        direction = analyze_environment_m1(closes_m1)
        bands = multi_bollinger({"S10": closes_s10})["S10"]
        return should_enter_trade_s10(direction, closes_s10, bands)
    if mode == "trend_follow":
        if len(closes_m1) < 2:
            return None
        last = closes_m1[-1]
        prev = closes_m1[-2]
        if last > prev:
            return "long"
        if last < prev:
            return "short"
    return None


__all__ = [
    "choose_strategy",
    "entry_signal",
    "ADX_SCALP_MIN",
    "ADX_TREND_MIN",
]
