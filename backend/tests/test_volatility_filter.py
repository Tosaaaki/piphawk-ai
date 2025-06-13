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


def _c(h):
    return {"mid": {"o": "0", "h": str(h), "l": "0", "c": "0"}}


class TestVolatilityFilter(unittest.TestCase):
    def setUp(self):
        import backend.filters.volatility_filter as vf
        importlib.reload(vf)
        self.vf = vf

    def test_block_short_true(self):
        atr = FakeSeries([1.0, 1.5, 2.0])
        candles = [_c(1.0), _c(1.1), _c(1.2)]
        self.assertTrue(self.vf.should_block_short(candles, atr))

    def test_block_short_false(self):
        atr = FakeSeries([1.0, 1.1, 1.15])
        candles = [_c(1.0), _c(1.0), _c(1.0)]
        self.assertFalse(self.vf.should_block_short(candles, atr))


if __name__ == '__main__':
    unittest.main()
