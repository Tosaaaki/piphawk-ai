import os
import sys
import types
import importlib
import unittest

class TestRegimeCaching(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
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
        self.oa._last_regime_ai_call_time = 0.0
        self.oa._cached_regime_result = None

    def tearDown(self):
        for name in getattr(self, "_mods", []):
            sys.modules.pop(name, None)

    def test_caches_market_condition(self):
        calls = []
        def dummy_ask(prompt, **kwargs):
            calls.append(prompt)
            return {"market_condition": "trend"}
        self.oa.ask_openai = dummy_ask
        ctx = {"indicators": {"adx": [30], "ema_slope": [0.1]}}
        first = self.oa.get_market_condition(ctx)
        second = self.oa.get_market_condition(ctx)
        self.assertEqual(len(calls), 1, "ask_openai should be called once")
        self.assertEqual(first, second)

if __name__ == "__main__":
    unittest.main()
