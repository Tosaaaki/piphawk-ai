from __future__ import annotations

"""ADX値に基づくシンプルなストラテジー切換ユーティリティ."""

from typing import Sequence, Optional
import logging

from backend.utils import env_loader

from indicators.bollinger import multi_bollinger
from signals.scalp_strategy import (
    analyze_environment_tf,
    analyze_environment_m1,
    should_enter_trade_s10,
)


ADX_SCALP_MIN = float(env_loader.get_env("ADX_SCALP_MIN", "20"))
ADX_TREND_MIN = float(env_loader.get_env("ADX_TREND_MIN", "30"))


def choose_strategy(adx_value: float) -> str:
    """ADXの値からモードを判定."""
    if adx_value < ADX_SCALP_MIN:
        return "none"
    if adx_value < ADX_TREND_MIN:
        return "scalp"
    return "trend_follow"


def determine_trade_mode(
    adx_value: float,
    closes_tf: Sequence[float],
    *,
    tf: str | None = None,
) -> str:
    """市場状態からトレードモードを返す."""
    logger = logging.getLogger(__name__)
    env = analyze_environment_tf(closes_tf, tf)

    mode = choose_strategy(adx_value)
    reason = ""

    if mode == "none":
        reason = f"ADX {adx_value:.1f} < {ADX_SCALP_MIN}"
    elif mode == "scalp":
        reason = f"{ADX_SCALP_MIN} <= ADX {adx_value:.1f} < {ADX_TREND_MIN}"
    else:  # trend_follow
        if env == "range":
            reason = f"{tf or 'M1'} range despite ADX {adx_value:.1f} >= {ADX_TREND_MIN}"
            mode = "scalp"
        else:
            reason = f"ADX {adx_value:.1f} >= {ADX_TREND_MIN} and {tf or 'M1'} trend"

    logger.info("determine_trade_mode -> %s (%s)", mode, reason)
    return mode


def entry_signal(
    adx_value: float,
    closes_m1: Sequence[float],
    closes_s10: Sequence[float],
) -> Optional[str]:
    """ADXとBBからモードを決定して方向を返す."""
    tf = env_loader.get_env("SCALP_COND_TF", "M1").upper()
    ref_closes = closes_s10 if tf == "S10" else closes_m1
    mode = determine_trade_mode(adx_value, ref_closes, tf=tf)
    if mode == "scalp":
        if tf == "S10":
            direction = analyze_environment_tf(closes_s10, tf)
        else:
            direction = analyze_environment_tf(closes_m1, tf)
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
    "determine_trade_mode",
    "entry_signal",
    "ADX_SCALP_MIN",
    "ADX_TREND_MIN",
]
