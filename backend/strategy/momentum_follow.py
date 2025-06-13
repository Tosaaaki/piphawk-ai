"""ブレイク後のモメンタムを利用した追随エントリー判定用モジュール."""

from typing import Dict, List, Optional

from backend.utils import env_loader


def follow_breakout(candles: List[dict], indicators: Dict[str, list], direction: Optional[str]) -> bool:
    """ブレイクアウト後に追随エントリーすべきか判定して返す.

    Parameters
    ----------
    candles : list of dict
        最新のローソク足データ
    indicators : dict
        ADX などの計算済み指標
    direction : str or None
        ブレイク方向 ``"up"`` もしくは ``"down"``

    Returns
    -------
    bool
        エントリーすべきと判断した場合 ``True``
    """

    if direction not in ("up", "down") or len(candles) < 2:
        return False

    adx_series = indicators.get("adx")
    atr_series = indicators.get("atr")
    if adx_series is None or atr_series is None:
        return False

    if not len(adx_series) or not len(atr_series):
        return False

    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    adx_min = float(env_loader.get_env("FOLLOW_ADX_MIN", "25"))
    pull_ratio = float(env_loader.get_env("FOLLOW_PULLBACK_ATR_RATIO", "0.5"))

    adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
    atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]

    if float(adx_val) < adx_min:
        return False

    breakout_candle = candles[-2]
    last_candle = candles[-1]

    if direction == "up":
        pull = float(breakout_candle["mid"]["h"]) - float(last_candle["mid"]["c"])
    else:
        pull = float(last_candle["mid"]["c"]) - float(breakout_candle["mid"]["l"])

    pull_pips = max(pull, 0.0) / pip_size
    atr_pips = float(atr_val) / pip_size

    return pull_pips <= atr_pips * pull_ratio
