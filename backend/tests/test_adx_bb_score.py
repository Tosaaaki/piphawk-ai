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
        if isinstance(idx, slice):
            return self._data[idx]
        if isinstance(idx, int) and idx < 0:
            raise KeyError(idx)
        return self._data[idx]
    def __len__(self):
        return len(self._data)

pandas_stub = types.ModuleType("pandas")
pandas_stub.Series = FakeSeries
sys.modules["pandas"] = pandas_stub

from backend.indicators.adx import calculate_adx_bb_score


class TestAdxBbScore(unittest.TestCase):
    def test_basic_score(self):
        adx = [20, 22, 25, 28]
        bb_u = [1.1, 1.2, 1.3, 1.4]
        bb_l = [1.0, 1.1, 1.2, 1.2]
        res = calculate_adx_bb_score(adx, bb_u, bb_l, lookback=3, width_period=4)
        self.assertAlmostEqual(res, 9.6)


if __name__ == "__main__":
    unittest.main()
