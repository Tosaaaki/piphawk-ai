import importlib
import os
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


class TestAdxSlopeBias(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LOCAL_WEIGHT_THRESHOLD"] = "0.6"
        os.environ["ADX_SLOPE_LOOKBACK"] = "3"
        self._added = []

        def add(name: str, mod: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._added.append(name)

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

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)
        os.environ.pop("ADX_SLOPE_LOOKBACK", None)
        os.environ.pop("OPENAI_API_KEY", None)
# Cleanup imported module to avoid side effects
        sys.modules.pop("backend.strategy.openai_analysis", None)

    def test_negative_slope_biases_range(self):
        self.oa.ask_openai = lambda *a, **k: {"market_condition": "range"}
        params = []
        def _calc(local, ai, **p):
            params.append(p)
            return 0.2
        self.oa.calc_consistency = _calc
        ctx = {"indicators": {"adx": [30, 28, 26, 24], "ema_slope": [0.1, 0.1, 0.1]}}
        res = self.oa.get_market_condition(ctx)
        self.assertEqual(res["market_condition"], "range")
        self.assertTrue(params)
        self.assertLess(params[-1].get("adx_ok", 1.0), 1.0)


if __name__ == "__main__":
    unittest.main()
