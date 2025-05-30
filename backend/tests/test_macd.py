import sys
import types
import importlib
import unittest

class FakeSeries:
    def __init__(self, data, *a, **k):
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
    def __sub__(self, other):
        if isinstance(other, FakeSeries):
            return FakeSeries([a - b for a, b in zip(self._data, other._data)])
        return FakeSeries([a - other for a in self._data])
    def diff(self, periods=1):
        data = [None] * periods
        for i in range(periods, len(self._data)):
            data.append(self._data[i] - self._data[i - periods])
        return FakeSeries(data)
    def ffill(self):
        return self
    def bfill(self):
        return self
    def tolist(self):
        return list(self._data)
    def ewm(self, span=None, adjust=False):
        data = [float(x) for x in self._data]
        alpha = 2 / (span + 1)
        ema = None
        result = []
        for v in data:
            ema = v if ema is None else ema + alpha * (v - ema)
            result.append(ema)
        class _EWM:
            def mean(self_inner):
                return FakeSeries(result)
        return _EWM()

class TestMACD(unittest.TestCase):
    def setUp(self):
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        sys.modules["pandas"] = pandas_stub
        sys.modules["numpy"] = types.ModuleType("numpy")
        sys.modules["numpy"] = types.ModuleType("numpy")
        import backend.indicators.macd as m
        importlib.reload(m)
        self.macd = m

    def tearDown(self):
        sys.modules.pop("numpy", None)

    def _ema(self, values, span):
        alpha = 2 / (span + 1)
        ema = None
        result = []
        for v in values:
            ema = v if ema is None else ema + alpha * (v - ema)
            result.append(ema)
        return result

    def test_macd_computation(self):
        prices = [1, 2, 3, 4, 5]
        macd_series, signal_series = self.macd.calculate_macd(
            prices, fast_period=3, slow_period=6, signal_period=3
        )
        hist_series = self.macd.calculate_macd_histogram(
            prices, fast_period=3, slow_period=6, signal_period=3
        )
        ema_fast = self._ema(prices, 3)
        ema_slow = self._ema(prices, 6)
        exp_macd = [f - s for f, s in zip(ema_fast, ema_slow)]
        exp_signal = self._ema(exp_macd, 3)
        exp_hist = [m - s for m, s in zip(exp_macd, exp_signal)]
        for a, b in zip(macd_series.tolist(), exp_macd):
            self.assertAlmostEqual(a, b, places=6)
        for a, b in zip(signal_series.tolist(), exp_signal):
            self.assertAlmostEqual(a, b, places=6)
        for a, b in zip(hist_series.tolist(), exp_hist):
            self.assertAlmostEqual(a, b, places=6)

class TestCalculateIndicatorsMACD(unittest.TestCase):
    def setUp(self):
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        sys.modules["pandas"] = pandas_stub
        sys.modules["numpy"] = types.ModuleType("numpy")
        mods = {
            "backend.indicators.rsi": {"calculate_rsi": lambda prices: FakeSeries(prices)},
            "backend.indicators.ema": {"calculate_ema": lambda prices, period=None: FakeSeries(prices)},
            "backend.indicators.atr": {"calculate_atr": lambda *a, **k: FakeSeries([0])},
            "backend.indicators.bollinger": {"calculate_bollinger_bands": lambda x: {"upper_band": FakeSeries(x), "lower_band": FakeSeries(x), "middle_band": FakeSeries(x)}},
            "backend.indicators.adx": {"calculate_adx": lambda *a, **k: FakeSeries([0])},
            "backend.indicators.pivot": {"calculate_pivots": lambda h,l,c: {"pivot":1,"r1":1,"s1":1,"r2":1,"s2":1}},
            "backend.indicators.n_wave": {"calculate_n_wave_target": lambda prices: 0.0},
            "backend.indicators.polarity": {"calculate_polarity": lambda prices: FakeSeries([0])},
            "backend.indicators.macd": {
                "calculate_macd": lambda prices, **k: (
                    FakeSeries([1] * len(prices)),
                    FakeSeries([0.5] * len(prices)),
                ),
                "calculate_macd_histogram": lambda prices, **k: FakeSeries([0.5] * len(prices)),
            }
        }
        self._added = ["numpy"]
        for name, attrs in mods.items():
            mod = types.ModuleType(name)
            for k, v in attrs.items():
                setattr(mod, k, v)
            sys.modules[name] = mod
            self._added.append(name)
        cf = types.ModuleType("backend.market_data.candle_fetcher")
        cf.fetch_candles = lambda *a, **k: []
        sys.modules["backend.market_data.candle_fetcher"] = cf
        self._added.append("backend.market_data.candle_fetcher")
        import backend.indicators.calculate_indicators as ci
        importlib.reload(ci)
        self.ci = ci

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_keys_present(self):
        data = [{"mid": {"c": "1", "h": "1", "l": "1"}, "complete": True}]
        result = self.ci.calculate_indicators(data)
        self.assertIn("macd", result)
        self.assertIn("macd_signal", result)
        self.assertIn("macd_hist", result)

if __name__ == "__main__":
    unittest.main()
