"""直近高値・安値を抜けたかのみを判定するブレイクアウトフィルター."""

from typing import Dict, List


def _get_val(candle: Dict, key: str) -> float:
    """Return float value from candle or its 'mid' subdict."""
    base = candle.get("mid", candle)
    return float(base.get(key))




def should_enter_breakout(candles: List[Dict], indicators: Dict) -> bool:
    """最新足が前足の高値または安値を超えた場合に True を返す."""
    if len(candles) < 2:
        return False

    last = candles[-1]
    prev = candles[-2]
    last_close = _get_val(last, "c")
    prev_high = _get_val(prev, "h")
    prev_low = _get_val(prev, "l")

    return last_close > prev_high or last_close < prev_low
