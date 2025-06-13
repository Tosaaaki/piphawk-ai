import importlib
import os
import sys
import types
import unittest


class TestMarketConditionCooldown(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["AI_REGIME_COOLDOWN_SEC"] = "60"
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

        oc = types.ModuleType("backend.utils.openai_client")
        self.calls = []
        def dummy_ask(prompt, **kwargs):
            self.calls.append(prompt)
            return {"market_condition": "trend"}
        oc.ask_openai = dummy_ask
        oc.AI_MODEL = "gpt"
        oc.set_call_limit = lambda *_a, **_k: None
        add_module("backend.utils.openai_client", oc)

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa
        self.oa._last_regime_ai_call_time = 0.0
        self.oa._cached_regime_result = None

    def tearDown(self):
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)
        os.environ.pop("AI_REGIME_COOLDOWN_SEC", None)

    def test_cached_result_returned_during_cooldown(self):
        ctx = {"indicators": {"adx": [30], "ema_slope": [0.1, 0.2]}}
        res1 = self.oa.get_market_condition(ctx)
        self.assertEqual(res1["market_condition"], "trend")
        res2 = self.oa.get_market_condition(ctx)
        self.assertEqual(res2, res1)
        self.assertEqual(len(self.calls), 1, "ask_openai should not be called twice")

if __name__ == "__main__":
    unittest.main()
