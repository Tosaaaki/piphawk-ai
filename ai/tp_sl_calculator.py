from __future__ import annotations

"""ATR を元に TP/SL を決定するヘルパー."""


def calc_tp_sl(regime: str, atr: float) -> tuple[int, int]:
    """レジーム別の TP/SL 値を返す."""
    if regime == "scalp":
        tp = int(max(3, min(12, 0.5 * atr)))
        sl = int(max(6, 1.0 * atr))
    else:
        tp = int(max(15, min(100, 2.0 * atr)))
        sl = int(max(20, 1.5 * atr))
    return tp, sl
