import pytest
from indicators.patterns import DoubleTopSignal


def test_double_top_signal_basic():
    candles = [
        {"o": 1.0, "h": 1.2, "l": 0.9, "c": 1.1, "volume": 100},
        {"o": 1.1, "h": 1.3, "l": 1.05, "c": 1.25, "volume": 120},
        {"o": 1.2, "h": 1.2, "l": 1.0, "c": 1.15, "volume": 180},
        {"o": 1.15, "h": 1.05, "l": 0.95, "c": 1.0, "volume": 160},
    ]
    sig = DoubleTopSignal(max_separation=3)
    result = sig.evaluate(candles)
    assert result is not None
    assert result["interval"] == 2
    assert result["neckline_ratio"] > 0
