import os
import sys
import types
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
        if isinstance(idx, slice):
            return self._data[idx]
        return self._data[idx]
    def __len__(self):
        return len(self._data)


class TestRapidReversalBlock(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._added.append(name)

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        add("requests", types.ModuleType("requests"))

        stub_names = [
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.market_data.tick_fetcher",
            "backend.strategy.higher_tf_analysis",
        ]
        for n in stub_names:
            add(n, types.ModuleType(n))

        sys.modules["backend.market_data.candle_fetcher"].fetch_candles = lambda *a, **k: []
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {"rsi": FakeSeries([50])}
        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: {}
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}

        os.environ["REVERSAL_RSI_DIFF"] = "10"
        os.environ["BAND_WIDTH_THRESH_PIPS"] = "3"
        os.environ["ATR_ENTRY_THRESHOLD"] = "0.09"
        os.environ["RSI_ENTRY_LOWER"] = "20"
        os.environ["RSI_ENTRY_UPPER"] = "80"
        os.environ["PIP_SIZE"] = "0.01"

        import backend.strategy.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)
        os.environ.pop("REVERSAL_RSI_DIFF", None)

    def _base_indicators(self):
        return {
            "rsi": FakeSeries([60]),
            "atr": FakeSeries([0.1]),
            "ema_fast": FakeSeries([1, 2]),
            "ema_slow": FakeSeries([2, 1]),
            "bb_upper": FakeSeries([1.2]),
            "bb_lower": FakeSeries([1.0]),
            "bb_middle": FakeSeries([1.1]),
            "adx": FakeSeries([30]),
            "macd_hist": FakeSeries([1.0]),
        }

    def test_rapid_reversal_helper(self):
        block = self.sf.rapid_reversal_block(
            FakeSeries([60]), FakeSeries([40]), FakeSeries([0.5])
        )
        self.assertTrue(block)
        block = self.sf.rapid_reversal_block(
            FakeSeries([40]), FakeSeries([60]), FakeSeries([-0.6])
        )
        self.assertTrue(block)
        block = self.sf.rapid_reversal_block(
            FakeSeries([55]), FakeSeries([50]), FakeSeries([0.2])
        )
        self.assertFalse(block)

    def test_filter_blocks_on_reversal(self):
        ind = self._base_indicators()
        ind15 = {"rsi": FakeSeries([40])}
        m1 = {"rsi": FakeSeries([29, 35])}
        res = self.sf.pass_entry_filter(ind, price=1.2, indicators_m1=m1, indicators_m15=ind15)
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
