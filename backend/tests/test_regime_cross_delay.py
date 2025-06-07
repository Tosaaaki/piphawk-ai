import unittest
from piphawk_ai.analysis.regime_detector import RegimeDetector


class DummyADX:
    def __init__(self):
        self.seq = [
            {"adx": 15, "delta": 0.5, "p": 25, "m": 20},
            {"adx": 18, "delta": 1.0, "p": 24, "m": 30},
            {"adx": 22, "delta": 1.0, "p": 23, "m": 31},
            {"adx": 26, "delta": 1.0, "p": 22, "m": 32},
        ]
        self.i = 0
        self.last_di_plus = None
        self.last_di_minus = None

    def update(self, _t):
        d = self.seq[self.i]
        self.i += 1
        self.last_di_plus = d["p"]
        self.last_di_minus = d["m"]
        return d["adx"], d["delta"]

    def direction(self):
        return "down"


class TestRegimeCrossDelay(unittest.TestCase):
    def test_delay(self):
        class Det(RegimeDetector):
            def __init__(self):
                super().__init__()
                self.adx = DummyADX()

        det = Det()
        tick = {"high": 1.1, "low": 1.0, "close": 1.05}
        det.update(tick)  # warmup
        res = det.update(tick)  # cross occurs
        self.assertFalse(res["transition"])
        det.update(tick)
        res = det.update(tick)
        self.assertTrue(res["transition"])


if __name__ == "__main__":
    unittest.main()
