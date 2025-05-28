"""ブレイク後のモメンタムを利用した追随エントリー判定用モジュール."""

from typing import List, Dict, Optional


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
    # TODO: Use pullback size after breakout and ADX value to decide entry
    return False
