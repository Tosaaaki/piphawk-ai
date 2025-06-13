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

from backend.indicators.n_wave import calculate_n_wave_target


class TestNWave(unittest.TestCase):
    def test_uptrend_target(self):
        prices = [1.0, 1.1, 1.2, 1.15, 1.25]
        res = calculate_n_wave_target(prices, lookback=5, pivot_range=1)
        self.assertAlmostEqual(res, 1.35)


if __name__ == "__main__":
    unittest.main()
