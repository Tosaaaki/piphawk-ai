import os
import sys
import types
import importlib
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

class TestConsistencyWeights(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LOCAL_WEIGHT_THRESHOLD"] = "0.6"
        os.environ["CONSISTENCY_WEIGHTS"] = "ema:0.1,adx:0.1,rsi:0.8"
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
        os.environ.pop("CONSISTENCY_WEIGHTS", None)

    def test_weight_from_env(self):
        alpha = self.oa.calc_consistency(
            "trend",
            "trend",
            ema_ok=1.0,
            adx_ok=1.0,
            rsi_cross_ok=1.0,
        )
        expected_local = 0.1 + 0.1 + 0.8
        expected_alpha = self.oa.LOCAL_WEIGHT_THRESHOLD * expected_local + (1 - self.oa.LOCAL_WEIGHT_THRESHOLD)
        self.assertAlmostEqual(alpha, expected_alpha)


if __name__ == "__main__":
    unittest.main()
