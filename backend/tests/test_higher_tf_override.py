import importlib
import os
import sys
import types
import unittest


class FakeSeries:
    def __init__(self, data=None):
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

class TestHigherTfOverride(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LOCAL_WEIGHT_THRESHOLD"] = "0.6"
        self._mods = []

        def add(name: str, mod: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._mods.append(name)

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
        for m in self._mods:
            sys.modules.pop(m, None)

    def test_no_override_when_local_range(self):
        self.oa.ask_openai = lambda *a, **k: {"market_condition": "trend"}
        calls = []
        def _calc(local, ai, **p):
            calls.append((local, ai))
            return 0.8
        self.oa.calc_consistency = _calc
        ctx = {
            "indicators": {"adx": [15, 16, 15], "ema_slope": [0.1, -0.1, 0.05]},
            "indicators_h1": {"adx": [30, 31, 32], "ema_slope": [0.2, 0.2, 0.2]},
        }
        res = self.oa.get_market_condition(ctx)
        self.assertEqual(calls[-1][0], "range")
        self.assertEqual(res["market_condition"], "range")


if __name__ == "__main__":
    unittest.main()
