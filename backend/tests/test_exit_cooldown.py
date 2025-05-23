import os
import sys
import types
import importlib
import unittest
import json

class TestExitDecisionCooldown(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ.setdefault("BE_TRIGGER_PIPS", "10")
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
        self.oa._last_exit_ai_call_time = 0.0

    def tearDown(self):
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)

    def test_exit_decision_skipped_during_cooldown(self):
        calls = []
        def dummy_ask(prompt, **kwargs):
            calls.append(prompt)
            return {}
        self.oa.ask_openai = dummy_ask
        pos = {"units": "1", "average_price": "1"}
        self.oa.get_exit_decision({}, pos, indicators_m1={})
        self.assertEqual(len(calls), 1)
        result = self.oa.get_exit_decision({}, pos, indicators_m1={})
        self.assertEqual(len(calls), 1, "ask_openai should not be called during cooldown")
        text = json.dumps(result) if isinstance(result, dict) else str(result)
        self.assertIn("Cooldown active", text)

if __name__ == "__main__":
    unittest.main()
