import unittest

from backend.indicators.keltner import calculate_keltner_bands
from backend.indicators.rolling import RollingKeltner


class DummyTick(dict):
    """簡易 tick オブジェクト."""

    def __getattr__(self, item):
        return self[item]


class TestKeltner(unittest.TestCase):
    def test_calculate_bands(self):
        high = [1, 2, 3, 4]
        low = [0.5, 1.5, 2.5, 3.5]
        close = [0.8, 1.8, 2.8, 3.8]
        bands = calculate_keltner_bands(high, low, close, window=2, atr_mult=1)
        self.assertEqual(len(bands["upper_band"]), 4)
        self.assertGreater(bands["upper_band"][-1], bands["middle_band"][-1])

    def test_rolling_keltner(self):
        rk = RollingKeltner(window=2, atr_mult=1)
        ticks = [
            DummyTick(high=1, low=0.9, close=0.95),
            DummyTick(high=1.1, low=1.0, close=1.05),
            DummyTick(high=1.2, low=1.1, close=1.15),
        ]
        bands = None
        for t in ticks:
            bands = rk.update(t)
        self.assertIsNotNone(bands)
        self.assertIn("upper", bands)
        self.assertTrue(bands["upper"] > bands["middle"])


if __name__ == "__main__":
    unittest.main()
