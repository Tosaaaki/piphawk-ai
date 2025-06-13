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

class TestCounterTrendBlock(unittest.TestCase):
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

    def test_ema_alignment_blocks(self):
        m5 = {"adx": FakeSeries([20, 30]), "ema_fast": FakeSeries([1, 1.1]), "ema_slow": FakeSeries([1, 1.05])}
        m15 = {"ema_fast": FakeSeries([1, 1.2]), "ema_slow": FakeSeries([1, 1.1])}
        h1 = {"ema_fast": FakeSeries([1, 1.3]), "ema_slow": FakeSeries([1, 1.2])}
        self.assertTrue(self.sf.counter_trend_block("short", m5, m15, h1))

    def test_adx_rising_blocks(self):
        m5 = {"adx": FakeSeries([24, 26]), "ema_fast": FakeSeries([1, 1.1]), "ema_slow": FakeSeries([1, 1.05])}
        self.assertTrue(self.sf.counter_trend_block("short", m5))

    def test_downtrend_blocks_long(self):
        m5 = {
            "adx": FakeSeries([26, 26]),
            "ema_fast": FakeSeries([1.1, 1.0]),
            "ema_slow": FakeSeries([1.05, 1.05]),
        }
        self.assertTrue(self.sf.counter_trend_block("long", m5))

    def test_uptrend_blocks_short(self):
        m5 = {
            "adx": FakeSeries([26, 26]),
            "ema_fast": FakeSeries([1.0, 1.1]),
            "ema_slow": FakeSeries([1.0, 1.05]),
        }
        self.assertTrue(self.sf.counter_trend_block("short", m5))

    def test_bypass_with_high_adx_same_direction(self):
        import os
        os.environ["COUNTER_BYPASS_ADX"] = "30"
        m5 = {
            "adx": FakeSeries([25, 35]),
            "ema_fast": FakeSeries([1.0, 1.1]),
            "ema_slow": FakeSeries([1.0, 1.05]),
        }
        m15 = {"ema_fast": FakeSeries([1.1, 1.0]), "ema_slow": FakeSeries([1.1, 1.05])}
        h1 = {"ema_fast": FakeSeries([1.2, 1.1]), "ema_slow": FakeSeries([1.2, 1.15])}
        self.assertFalse(self.sf.counter_trend_block("long", m5, m15, h1))
        os.environ.pop("COUNTER_BYPASS_ADX", None)

if __name__ == "__main__":
    unittest.main()
