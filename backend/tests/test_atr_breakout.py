import unittest

from backend.strategy.range_break import detect_atr_breakout


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


class TestAtrBreakout(unittest.TestCase):
    def test_breakout_up(self):
        candles = [
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.92"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.93"}, "complete": True},
            {"mid": {"h": "1.2", "l": "0.9", "c": "1.12"}, "complete": True},
        ]
        atr = FakeSeries([0.2])
        res = detect_atr_breakout(candles, atr, lookback=3)
        self.assertEqual(res, "up")

    def test_breakout_down(self):
        candles = [
            {"mid": {"h": "1.1", "l": "1.0", "c": "1.05"}, "complete": True},
            {"mid": {"h": "1.1", "l": "1.0", "c": "1.03"}, "complete": True},
            {"mid": {"h": "1.1", "l": "1.0", "c": "1.04"}, "complete": True},
            {"mid": {"h": "1.1", "l": "0.8", "c": "0.88"}, "complete": True},
        ]
        atr = FakeSeries([0.2])
        res = detect_atr_breakout(candles, atr, lookback=3)
        self.assertEqual(res, "down")

    def test_no_breakout(self):
        candles = [
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.92"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.93"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "1.02"}, "complete": True},
        ]
        atr = FakeSeries([0.2])
        res = detect_atr_breakout(candles, atr, lookback=3)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
