import unittest

from analysis.regime_detector import ATRBoostDetector


class DummyTick(dict):
    def __getattr__(self, item):
        return self[item]


def make_tick(high, low, close):
    return DummyTick(high=high, low=low, close=close)


class TestATRBoostDetector(unittest.TestCase):
    def test_detect_boost(self):
        det = ATRBoostDetector(length=3, threshold=1.2)
        for _ in range(3):
            self.assertFalse(det.update(make_tick(1.05, 0.95, 1.0)))
        res = det.update(make_tick(1.5, 0.7, 1.2))
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
