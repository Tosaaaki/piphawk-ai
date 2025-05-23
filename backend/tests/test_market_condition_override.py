import os
import sys
import types
import importlib
import unittest

class TestMarketConditionOverride(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._added_modules = []

        def add_module(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added_modules.append(name)

        add_module("pandas", types.ModuleType("pandas"))
        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add_module("openai", openai_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add_module("dotenv", dotenv_stub)
        add_module("requests", types.ModuleType("requests"))
        add_module("numpy", types.ModuleType("numpy"))

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)

    def test_local_range_overrides_llm_trend(self):
        self.oa.ask_openai = lambda *a, **k: "trend"
        ctx = {"indicators": {"adx": [10, 12, 11], "ema_slope": [0.1, 0.1, 0.1]}}
        with self.assertLogs(self.oa.logger, level="WARNING") as cm:
            res = self.oa.get_market_condition(ctx)
        self.assertEqual(res, "range")
        self.assertTrue(any("conflicts" in m for m in cm.output))

    def test_local_trend_overrides_llm_range(self):
        self.oa.ask_openai = lambda *a, **k: "range"
        ctx = {"indicators": {"adx": [25, 26, 27], "ema_slope": [-0.2, -0.3, -0.1]}}
        with self.assertLogs(self.oa.logger, level="WARNING") as cm:
            res = self.oa.get_market_condition(ctx)
        self.assertEqual(res, "trend")
        self.assertTrue(any("conflicts" in m for m in cm.output))

if __name__ == "__main__":
    unittest.main()
