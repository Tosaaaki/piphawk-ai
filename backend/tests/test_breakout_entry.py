import os
import importlib
import unittest

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


def _c(o, h, l, c):
    return {"mid": {"o": str(o), "h": str(h), "l": str(l), "c": str(c)}}


class TestBreakoutEntry(unittest.TestCase):
    def setUp(self):
        os.environ["BREAKOUT_ADX_MIN"] = "30"
        import backend.filters.breakout_entry as be
        importlib.reload(be)
        self.be = be

    def tearDown(self):
        os.environ.pop("BREAKOUT_ADX_MIN", None)

    def test_breakout_true(self):
        indicators = {"adx": FakeSeries([35])}
        candles = [_c(1.0, 1.1, 0.9, 1.05), _c(1.05, 1.2, 1.0, 1.21)]
        self.assertTrue(self.be.should_enter_breakout(candles, indicators))

    def test_breakout_false_low_adx(self):
        indicators = {"adx": FakeSeries([20])}
        candles = [_c(1.0, 1.1, 0.9, 1.05), _c(1.05, 1.2, 1.0, 1.21)]
        self.assertFalse(self.be.should_enter_breakout(candles, indicators))


if __name__ == "__main__":
    unittest.main()
