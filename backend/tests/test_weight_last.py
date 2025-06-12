import sys
import types
import importlib
import unittest


class FakeSeries:
    def __init__(self, data=None, *a, **k):
        self._data = list(data or [])
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
    def diff(self, periods=1):
        return FakeSeries([0]*len(self._data))
    def ffill(self):
        return self
    def bfill(self):
        return self


def _c(vol, complete=True):
    return {"mid": {"c": "1", "h": "1", "l": "1"}, "volume": vol, "complete": complete}


class TestWeightLast(unittest.TestCase):
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
            "backend.indicators.adx": {
                "calculate_adx": lambda *a, **k: FakeSeries([0]),
                "calculate_adx_bb_score": lambda *a, **k: 0.0,
                "calculate_di": lambda *a, **k: (FakeSeries([0]), FakeSeries([0])),
            },
            "backend.indicators.pivot": {"calculate_pivots": lambda h,l,c: {"pivot":1,"r1":1,"s1":1,"r2":1,"s2":1}},
            "backend.indicators.n_wave": {"calculate_n_wave_target": lambda prices: 0.0},
            "backend.indicators.polarity": {"calculate_polarity": lambda prices: FakeSeries([0])},
            "backend.indicators.macd": {
                "calculate_macd": lambda prices, **k: (FakeSeries([0]*len(prices)), FakeSeries([0]*len(prices))),
                "calculate_macd_histogram": lambda prices, **k: FakeSeries([0]*len(prices)),
            },
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

    def test_weight_last_zero_avg(self):
        data = [_c(0, True) for _ in range(6)] + [_c(0, False)]
        result = self.ci.calculate_indicators(data)
        self.assertEqual(result.get("weight_last"), 1.0)

    def test_weight_last_zero_volume(self):
        data = [_c(100, True) for _ in range(6)] + [_c(0, False)]
        result = self.ci.calculate_indicators(data)
        self.assertEqual(result.get("weight_last"), 0.5)

    def test_weight_last_clamped(self):
        data = [_c(100, True) for _ in range(6)] + [_c(400, False)]
        result = self.ci.calculate_indicators(data)
        self.assertEqual(result.get("weight_last"), 1.0)


if __name__ == "__main__":
    unittest.main()
