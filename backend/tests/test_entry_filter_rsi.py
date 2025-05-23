import os
import unittest
import datetime
import types
import sys

pass_entry_filter = None
_rsi_cross_up_or_down = None


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


class TestEntryFilterRSICross(unittest.TestCase):
    def setUp(self):
        self._added_modules = []

        def add_module(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added_modules.append(name)

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add_module("pandas", pandas_stub)
        add_module("requests", types.ModuleType("requests"))

        stub_modules = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.higher_tf_analysis",
        ]
        for name in stub_modules:
            mod = types.ModuleType(name)
            add_module(name, mod)

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: {}
        sys.modules["backend.market_data.candle_fetcher"].fetch_candles = lambda *a, **k: []
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {"rsi": FakeSeries([20, 40])}
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}

        global pass_entry_filter, _rsi_cross_up_or_down
        import importlib
        from backend.strategy import signal_filter as sf
        importlib.reload(sf)
        pass_entry_filter = sf.pass_entry_filter
        _rsi_cross_up_or_down = sf._rsi_cross_up_or_down
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        start = (now.hour + 1) % 24
        end = (start + 1) % 24
        os.environ["QUIET_START_HOUR_JST"] = str(start)
        os.environ["QUIET_END_HOUR_JST"] = str(end)
        os.environ["HIGHER_TF_ENABLED"] = "false"
        os.environ["PIP_SIZE"] = "0.01"
        os.environ["BAND_WIDTH_THRESH_PIPS"] = "4"
        os.environ["ATR_ENTRY_THRESHOLD"] = "0.09"
        os.environ["RSI_ENTRY_LOWER"] = "20"
        os.environ["RSI_ENTRY_UPPER"] = "80"
        os.environ["DISABLE_ENTRY_FILTER"] = "false"
        os.environ.pop("RSI_CROSS_LOOKBACK", None)

    def tearDown(self):
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)

    def _base_indicators(self):
        return {
            "rsi": FakeSeries([50, 50]),
            "atr": FakeSeries([0.1, 0.1]),
            "ema_fast": FakeSeries([1, 2]),
            "ema_slow": FakeSeries([2, 1]),
            "bb_upper": FakeSeries([1.2, 1.3]),
            "bb_lower": FakeSeries([1.0, 1.1]),
            "bb_middle": FakeSeries([1.1, 1.2]),
            "adx": FakeSeries([30, 30]),
        }

    def test_rsi_cross_signal_helper(self):
        self.assertTrue(_rsi_cross_up_or_down(FakeSeries([25, 35])))
        self.assertTrue(_rsi_cross_up_or_down(FakeSeries([75, 65])))
        self.assertFalse(_rsi_cross_up_or_down(FakeSeries([31, 33])))
        self.assertTrue(_rsi_cross_up_or_down(FakeSeries([25, 32, 36]), lookback=2))

    def test_pass_entry_filter_blocks_without_cross(self):
        ind = self._base_indicators()
        m1 = {"rsi": FakeSeries([31, 33])}
        result = pass_entry_filter(ind, price=1.2, indicators_m1=m1)
        self.assertFalse(result)

    def test_pass_entry_filter_allows_with_cross_up(self):
        ind = self._base_indicators()
        m1 = {"rsi": FakeSeries([29, 35])}
        result = pass_entry_filter(ind, price=1.2, indicators_m1=m1)
        self.assertTrue(result)

    def test_pass_entry_filter_allows_with_cross_down(self):
        ind = self._base_indicators()
        m1 = {"rsi": FakeSeries([75, 65])}
        result = pass_entry_filter(ind, price=1.2, indicators_m1=m1)
        self.assertTrue(result)

    def test_pass_entry_filter_lookback_env(self):
        os.environ["RSI_CROSS_LOOKBACK"] = "3"
        ind = self._base_indicators()
        m1 = {"rsi": FakeSeries([28, 31, 32, 36])}
        result = pass_entry_filter(ind, price=1.2, indicators_m1=m1)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()

