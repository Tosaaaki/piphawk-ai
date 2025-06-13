import unittest

from indicators.candlestick import detect_upper_wick_cluster


class TestWickDetection(unittest.TestCase):
    def test_detect_upper_wick_cluster_true(self):
        candles = [
            {"o": 1.0, "h": 1.2, "l": 0.9, "c": 1.1},
            {"o": 1.1, "h": 1.3, "l": 1.0, "c": 1.15},
            {"o": 1.15, "h": 1.35, "l": 1.1, "c": 1.2},
        ]
        self.assertTrue(detect_upper_wick_cluster(candles, ratio=0.5, count=3))

    def test_detect_upper_wick_cluster_false(self):
        candles = [
            {"o": 1.0, "h": 1.05, "l": 0.95, "c": 1.03},
            {"o": 1.02, "h": 1.06, "l": 0.99, "c": 1.05},
            {"o": 1.05, "h": 1.07, "l": 1.0, "c": 1.06},
        ]
        self.assertFalse(detect_upper_wick_cluster(candles, ratio=0.5, count=3))


if __name__ == "__main__":
    unittest.main()
