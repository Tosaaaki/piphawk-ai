import importlib
import os
import sys
import types
import unittest


class TestMarketDiCrossFloat(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LOCAL_WEIGHT_THRESHOLD"] = "0.6"
        self._mods = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._mods.append(name)
        add("pandas", types.ModuleType("pandas"))
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
        for name in self._mods:
            sys.modules.pop(name, None)

    def test_float_values_handled(self):
        self.oa.ask_openai = lambda *a, **k: {"market_condition": "range"}
        ctx = {"indicators": {"plus_di": 20.0, "minus_di": 30.0}}
        res = self.oa.get_market_condition(ctx)
        self.assertIn("market_condition", res)

if __name__ == "__main__":
    unittest.main()
