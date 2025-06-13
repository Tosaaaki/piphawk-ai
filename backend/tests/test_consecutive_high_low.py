import importlib
import sys
import types
import unittest


class TestConsecutiveHighLow(unittest.TestCase):
    def setUp(self):
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = lambda *a, **k: None
        sys.modules["pandas"] = pandas_stub
        sys.modules.setdefault("requests", types.ModuleType("requests"))
        import backend.strategy.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf

    def tearDown(self):
        sys.modules.pop("pandas", None)

    def test_lower_lows_true(self):
        candles = [
            {"mid": {"l": 3}},
            {"mid": {"l": 2}},
            {"mid": {"l": 1}},
            {"mid": {"l": 0}},
        ]
        self.assertTrue(self.sf.consecutive_lower_lows(candles, count=3))

    def test_lower_lows_false(self):
        candles = [
            {"mid": {"l": 3}},
            {"mid": {"l": 2}},
            {"mid": {"l": 2.5}},
            {"mid": {"l": 1}},
        ]
        self.assertFalse(self.sf.consecutive_lower_lows(candles, count=3))

    def test_higher_highs_true(self):
        candles = [
            {"mid": {"h": 0}},
            {"mid": {"h": 1}},
            {"mid": {"h": 2}},
            {"mid": {"h": 3}},
        ]
        self.assertTrue(self.sf.consecutive_higher_highs(candles, count=3))

    def test_higher_highs_false(self):
        candles = [
            {"mid": {"h": 0}},
            {"mid": {"h": 1}},
            {"mid": {"h": 0.5}},
            {"mid": {"h": 2}},
        ]
        self.assertFalse(self.sf.consecutive_higher_highs(candles, count=3))


if __name__ == "__main__":
    unittest.main()
