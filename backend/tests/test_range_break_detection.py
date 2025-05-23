import unittest

from backend.strategy.range_break import detect_range_break, classify_breakout


class FakeSeries:
    def __init__(self, data):
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


class TestRangeBreakDetection(unittest.TestCase):
    def test_detect_breakout_up(self):
        candles = [
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.92"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.93"}, "complete": True},
            {"mid": {"h": "1.1", "l": "0.9", "c": "1.11"}, "complete": True},
        ]
        res = detect_range_break(candles, lookback=3)
        self.assertTrue(res["break"])
        self.assertEqual(res["direction"], "up")

    def test_classify_trend(self):
        indicators = {"adx": FakeSeries([20, 30]), "ema_slope": FakeSeries([0.1, 0.2])}
        cls = classify_breakout(indicators)
        self.assertEqual(cls, "trend")

    def test_classify_range(self):
        indicators = {"adx": FakeSeries([10, 15]), "ema_slope": FakeSeries([0.01, 0.02])}
        cls = classify_breakout(indicators)
        self.assertEqual(cls, "range")


if __name__ == "__main__":
    unittest.main()
