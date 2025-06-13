import importlib
import sys
import types
import unittest


class TestHigherTFPivot(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._added.append(name)
        fetcher = types.ModuleType("backend.market_data.candle_fetcher")
        self.day_count = None
        def fake_fetch_candles(pair, granularity="M1", count=0):
            if granularity == "D":
                self.day_count = count
                return [{"complete": True, "mid": {"h": "2", "l": "1", "c": "1.5"}}]
            if granularity == "H4":
                return [
                    {"complete": True, "mid": {"h": "1.2", "l": "0.8", "c": "1.0"}},
                    {"complete": True, "mid": {"h": "1.1", "l": "0.9", "c": "1.0"}},
                ]
            if granularity == "H1":
                return [{"complete": True, "mid": {"h": "1.05", "l": "0.95", "c": "1.0"}}]
            return []
        fetcher.fetch_candles = fake_fetch_candles
        add("backend.market_data.candle_fetcher", fetcher)
        add("pandas", types.ModuleType("pandas"))
        import backend.strategy.higher_tf_analysis as hta
        importlib.reload(hta)
        self.hta = hta

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_returns_additional_pivots(self):
        res = self.hta.analyze_higher_tf("USD_JPY")
        self.assertEqual(res["pivot_d"], 1.5)
        self.assertEqual(res["pivot_h4"], 1.0)
        self.assertEqual(res["pivot_h1"], 1.0)
        self.assertEqual(self.day_count, 201)

if __name__ == "__main__":
    unittest.main()
