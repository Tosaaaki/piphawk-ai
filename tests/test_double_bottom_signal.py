import pytest
from indicators.patterns import DoubleBottomSignal


def test_double_bottom_signal_basic():
    candles = [
        {"o": 1.2, "h": 1.25, "l": 1.0, "c": 1.1, "volume": 100},
        {"o": 1.1, "h": 1.3, "l": 1.1, "c": 1.2, "volume": 110},
        {"o": 1.2, "h": 1.24, "l": 1.0, "c": 1.1, "volume": 180},
        {"o": 1.15, "h": 1.35, "l": 1.1, "c": 1.3, "volume": 160},
    ]
    sig = DoubleBottomSignal(max_separation=3)
    result = sig.evaluate(candles)
    assert result is not None
    assert result["interval"] == 2
    assert result["neckline_ratio"] > 0

