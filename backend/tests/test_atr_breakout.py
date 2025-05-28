import os
import sys
import types
import importlib
import unittest

from backend.strategy.range_break import detect_atr_breakout


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


class TestAtrBreakout(unittest.TestCase):
    def test_breakout_up(self):
        candles = [
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.92"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.93"}, "complete": True},
            {"mid": {"h": "1.2", "l": "0.9", "c": "1.12"}, "complete": True},
        ]
        atr = FakeSeries([0.2])
        res = detect_atr_breakout(candles, atr, lookback=3)
        self.assertEqual(res, "up")

    def test_breakout_down(self):
        candles = [
            {"mid": {"h": "1.1", "l": "1.0", "c": "1.05"}, "complete": True},
            {"mid": {"h": "1.1", "l": "1.0", "c": "1.03"}, "complete": True},
            {"mid": {"h": "1.1", "l": "1.0", "c": "1.04"}, "complete": True},
            {"mid": {"h": "1.1", "l": "0.8", "c": "0.88"}, "complete": True},
        ]
        atr = FakeSeries([0.2])
        res = detect_atr_breakout(candles, atr, lookback=3)
        self.assertEqual(res, "down")

    def test_no_breakout(self):
        candles = [
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.92"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "0.93"}, "complete": True},
            {"mid": {"h": "1.0", "l": "0.9", "c": "1.02"}, "complete": True},
        ]
        atr = FakeSeries([0.2])
        res = detect_atr_breakout(candles, atr, lookback=3)
        self.assertIsNone(res)


class TestMarketConditionAtrBreak(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LOCAL_WEIGHT_THRESHOLD"] = "0.6"
        self._added_modules = []

        def add(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added_modules.append(name)

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        openai_stub = types.ModuleType("openai")

        class DummyClient:
            def __init__(self, *a, **k):
                pass

        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add("openai", openai_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)
        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {"market_condition": "range"}
        oc.AI_MODEL = "gpt"
        add("backend.utils.openai_client", oc)

        import importlib
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        oa.detect_range_break = lambda candles, pivot=None: {"break": False, "direction": None}
        oa.detect_atr_breakout = lambda *a, **k: "up"
        oa.classify_breakout = lambda indicators: "range"
        self.oa = oa

    def tearDown(self):
        for name in self._added_modules:
            sys.modules.pop(name, None)

    def test_market_condition_returns_atr_direction(self):
        ctx = {"indicators": {"adx": [30], "atr": [0.2]}, "candles_m5": [{"mid": {"h": "1", "l": "0", "c": "1"}}]}
        res = self.oa.get_market_condition(ctx)
        self.assertEqual(res["market_condition"], "break")
        self.assertEqual(res["break_direction"], "up")


if __name__ == "__main__":
    unittest.main()
