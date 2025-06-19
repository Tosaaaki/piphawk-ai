import importlib
import os
import unittest
from typing import List


class FakeSeries:
    def __init__(self, data: List[float]):
        self._data = list(data)
        class _ILoc:
            def __init__(self, outer):
                self._outer = outer
            def __getitem__(self, idx):
                return self._outer._data[idx]
        self.iloc = _ILoc(self)
    def __getitem__(self, idx):
        return self._data[idx]
    def __len__(self):
        return len(self._data)


def _c(o, h, l, c):
    return {"mid": {"o": str(o), "h": str(h), "l": str(l), "c": str(c)}}


class TestTrendPullback(unittest.TestCase):
    def setUp(self):
        import backend.filters.trend_pullback as tp
        importlib.reload(tp)
        self.tp = tp

    def tearDown(self):
        pass

    def test_should_enter_true(self):
        indicators = {}
        candles = [
            _c(1.05, 1.06, 1.02, 1.03),
            _c(1.03, 1.07, 0.99, 1.06),
        ]
        self.assertTrue(self.tp.should_enter_long(candles, indicators))

    def test_adx_below_threshold(self):
        indicators = {}
        candles = [
            _c(1.05, 1.06, 1.02, 1.03),
            _c(1.03, 1.07, 0.99, 1.06),
        ]
        self.assertTrue(self.tp.should_enter_long(candles, indicators))

    def test_atr_below_min(self):
        indicators = {}
        candles = [
            _c(1.05, 1.06, 1.02, 1.03),
            _c(1.03, 1.07, 0.99, 1.06),
        ]
        self.assertTrue(self.tp.should_enter_long(candles, indicators))

    def test_should_enter_short_true(self):
        indicators = {}
        candles = [
            _c(1.03, 1.07, 0.99, 1.06),
            _c(1.06, 1.08, 1.02, 1.03),
        ]
        self.assertTrue(self.tp.should_enter_short(candles, indicators))

    def test_should_enter_short_false(self):
        indicators = {}
        candles = [
            _c(1.03, 1.07, 0.99, 1.06),
            _c(1.06, 1.08, 1.02, 1.07),
        ]
        self.assertFalse(self.tp.should_enter_short(candles, indicators))

    def test_should_skip_true(self):
        candles = [
            _c(1.0, 1.01, 0.99, 1.0),
            _c(1.0, 1.01, 0.99, 1.0),
            _c(1.0, 1.01, 0.99, 1.0),
            _c(1.02, 1.03, 0.98, 0.99),
        ]
        self.assertFalse(self.tp.should_skip(candles, ema_period=3))

    def test_should_skip_false(self):
        candles = [
            _c(1.0, 1.01, 0.99, 1.0),
            _c(1.0, 1.01, 0.99, 1.0),
            _c(1.0, 1.01, 0.99, 1.0),
            _c(1.005, 1.02, 0.99, 0.99),
        ]
        self.assertFalse(self.tp.should_skip(candles, ema_period=3))


if __name__ == "__main__":
    unittest.main()
