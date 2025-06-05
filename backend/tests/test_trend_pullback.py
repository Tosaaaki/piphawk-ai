import os
import importlib
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
        os.environ["PIP_SIZE"] = "0.01"
        os.environ["TREND_PB_ADX"] = "25"
        os.environ["TREND_PB_MIN_ATR_PIPS"] = "5"
        import backend.filters.trend_pullback as tp
        importlib.reload(tp)
        self.tp = tp

    def tearDown(self):
        os.environ.pop("PIP_SIZE", None)
        os.environ.pop("TREND_PB_ADX", None)
        os.environ.pop("TREND_PB_MIN_ATR_PIPS", None)

    def test_should_enter_true(self):
        indicators = {
            "adx": FakeSeries([20, 30]),
            "ema_fast": FakeSeries([1.0, 1.05]),
            "ema_slow": FakeSeries([0.99, 1.02]),
            "atr": FakeSeries([0.1]),
        }
        candles = [
            _c(1.05, 1.06, 1.02, 1.03),
            _c(1.03, 1.07, 0.99, 1.06),
        ]
        self.assertTrue(self.tp.should_enter_long(candles, indicators))

    def test_adx_below_threshold(self):
        indicators = {
            "adx": FakeSeries([10]),
            "ema_fast": FakeSeries([1.0, 1.05]),
            "ema_slow": FakeSeries([0.99, 1.02]),
            "atr": FakeSeries([0.1]),
        }
        candles = [
            _c(1.05, 1.06, 1.02, 1.03),
            _c(1.03, 1.07, 0.99, 1.06),
        ]
        self.assertFalse(self.tp.should_enter_long(candles, indicators))

    def test_atr_below_min(self):
        indicators = {
            "adx": FakeSeries([30]),
            "ema_fast": FakeSeries([1.0, 1.05]),
            "ema_slow": FakeSeries([0.99, 1.02]),
            "atr": FakeSeries([0.02]),
        }
        candles = [
            _c(1.05, 1.06, 1.02, 1.03),
            _c(1.03, 1.07, 0.99, 1.06),
        ]
        self.assertFalse(self.tp.should_enter_long(candles, indicators))

    def test_should_enter_short_true(self):
        indicators = {
            "adx": FakeSeries([20, 30]),
            "ema_fast": FakeSeries([1.05, 1.0]),
            "ema_slow": FakeSeries([1.05, 1.04]),
            "atr": FakeSeries([0.1]),
        }
        candles = [
            _c(1.03, 1.07, 0.99, 1.06),
            _c(1.06, 1.08, 1.02, 1.03),
        ]
        self.assertTrue(self.tp.should_enter_short(candles, indicators))

    def test_should_enter_short_false(self):
        indicators = {
            "adx": FakeSeries([20, 30]),
            "ema_fast": FakeSeries([1.05, 1.0]),
            "ema_slow": FakeSeries([1.05, 1.04]),
            "atr": FakeSeries([0.1]),
        }
        candles = [
            _c(1.03, 1.07, 0.99, 1.06),
            _c(1.06, 1.08, 1.02, 1.07),
        ]
        self.assertFalse(self.tp.should_enter_short(candles, indicators))


if __name__ == "__main__":
    unittest.main()
