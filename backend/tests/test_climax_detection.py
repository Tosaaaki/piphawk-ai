import importlib
import sys
import types
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

class TestClimaxDetection(unittest.TestCase):
    def setUp(self):
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        sys.modules["pandas"] = pandas_stub
        sys.modules.setdefault("requests", types.ModuleType("requests"))
        import backend.strategy.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf

    def tearDown(self):
        sys.modules.pop("pandas", None)

    def test_detect_climax_reversal_short(self):
        candles = [{"mid": {"c": 1.2}}]
        atr_vals = [0.01]*50 + [0.03]
        ind = {
            "bb_upper": FakeSeries([1.1]),
            "bb_lower": FakeSeries([0.9]),
            "atr": FakeSeries(atr_vals)
        }
        side = self.sf.detect_climax_reversal(candles, ind, lookback=50, z_thresh=1.5)
        self.assertEqual(side, "short")

    def test_detect_climax_reversal_long(self):
        candles = [{"mid": {"c": 0.8}}]
        atr_vals = [0.01]*50 + [0.03]
        ind = {
            "bb_upper": FakeSeries([1.1]),
            "bb_lower": FakeSeries([0.9]),
            "atr": FakeSeries(atr_vals)
        }
        side = self.sf.detect_climax_reversal(candles, ind, lookback=50, z_thresh=1.5)
        self.assertEqual(side, "long")

if __name__ == "__main__":
    unittest.main()
