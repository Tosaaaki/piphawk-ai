import unittest

from piphawk_ai.analysis.regime_detector import RegimeDetector


class DummyADX:
    def update(self, tick):
        return 23.0, 0.0

class DummyATR:
    def update(self, tick):
        return 1.4


class TestBreakoutEntryMethod(unittest.TestCase):
    def test_detect_breakout(self):
        det = RegimeDetector(low_window=3)
        det.adx = DummyADX()
        det.atr = DummyATR()
        for p in [1.0, 1.01, 1.02]:
            price = {"high": p + 0.1, "low": p - 0.1, "close": p}
            det.breakout_entry(price)
        signal = det.breakout_entry({"high": 0.95, "low": 0.9, "close": 0.91})
        self.assertEqual(signal, {"side": "short", "type": "breakout"})


if __name__ == "__main__":
    unittest.main()
