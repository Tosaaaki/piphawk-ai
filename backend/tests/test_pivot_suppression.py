import os
import sys
import types
import importlib
import unittest
import datetime

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

class TestPivotSuppression(unittest.TestCase):
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

        mods = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.higher_tf_analysis",
        ]
        for m in mods:
            mod = types.ModuleType(m)
            add(m, mod)

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: {"prices": [{"bids": [{"price": "1.0"}]}]}
        sys.modules["backend.market_data.candle_fetcher"].fetch_candles = lambda *a, **k: []
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {
            "rsi": FakeSeries([50, 50]),
            "atr": FakeSeries([0.1, 0.1]),
            "ema_fast": FakeSeries([1, 2]),
            "ema_slow": FakeSeries([2, 1]),
            "bb_upper": FakeSeries([1.2, 1.3]),
            "bb_lower": FakeSeries([1.0, 1.1]),
            "bb_middle": FakeSeries([1.1, 1.2]),
            "adx": FakeSeries([30, 30]),
        }
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {"pivot_d": 1.0, "pivot_h4": 1.0}

        now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        start = (now.hour + 1) % 24
        end = (start + 1) % 24
        os.environ["QUIET_START_HOUR_JST"] = str(start)
        os.environ["QUIET_END_HOUR_JST"] = str(end)
        os.environ["HIGHER_TF_ENABLED"] = "true"
        os.environ["PIVOT_SUPPRESSION_TFS"] = "D,H4"
        os.environ["PIVOT_SUPPRESSION_PIPS"] = "15"
        os.environ["PIP_SIZE"] = "0.01"
        os.environ["DISABLE_ENTRY_FILTER"] = "false"
        os.environ["BAND_WIDTH_THRESH_PIPS"] = "3"
        os.environ["ATR_ENTRY_THRESHOLD"] = "0.09"
        os.environ["RSI_ENTRY_LOWER"] = "20"
        os.environ["RSI_ENTRY_UPPER"] = "80"

        import backend.strategy.signal_filter as sf
        importlib.reload(sf)
        self.pass_entry_filter = sf.pass_entry_filter

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_blocked_by_pivot(self):
        m1 = {"rsi": FakeSeries([29, 35])}
        res = self.pass_entry_filter(sys.modules["backend.indicators.calculate_indicators"].calculate_indicators(), price=1.0, indicators_m1=m1)
        self.assertFalse(res)

if __name__ == "__main__":
    unittest.main()
