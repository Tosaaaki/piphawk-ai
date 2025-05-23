import os
import sys
import types
import importlib
import unittest
import json

class TestExitPatternOverride(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ.setdefault("BE_TRIGGER_PIPS", "10")
        self._added = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._added.append(name)
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
        self.oa._last_exit_ai_call_time = 0.0

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def test_override_on_matching_pattern(self):
        self.oa.ask_openai = lambda *a, **k: {"action": "EXIT", "reason": "double_top detected"}
        pos = {"units": "-1", "average_price": "1"}
        res = self.oa.get_exit_decision({}, pos, indicators_m1={})
        data = res if isinstance(res, dict) else json.loads(res)
        self.assertEqual(data.get("action"), "HOLD")

    def test_no_override_on_opposite_pattern(self):
        self.oa.ask_openai = lambda *a, **k: {"action": "EXIT", "reason": "double_top detected"}
        pos = {"units": "1", "average_price": "1"}
        res = self.oa.get_exit_decision({}, pos, indicators_m1={})
        data = res if isinstance(res, dict) else json.loads(res)
        self.assertEqual(data.get("action"), "EXIT")

if __name__ == "__main__":
    unittest.main()
