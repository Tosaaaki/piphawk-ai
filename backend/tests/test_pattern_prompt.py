import os
import sys
import types
import importlib
import unittest

class TestPatternPrompt(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
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
        pattern_mod = types.ModuleType("backend.strategy.pattern_ai_detection")
        pattern_mod.detect_chart_pattern = lambda *a, **k: {"pattern": "double_bottom"}
        add("backend.strategy.pattern_ai_detection", pattern_mod)
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def test_trade_plan_includes_pattern(self):
        captured = []
        self.oa.ask_openai = lambda prompt, **k: (captured.append(prompt) or '{"entry": {"side": "no"}}')
        candles = {"M5": [{"o":1,"h":2,"l":0.5,"c":1.5}]}
        self.oa.get_trade_plan({}, {"M5": {}}, candles, patterns=["double_bottom"])
        self.assertTrue(captured)
        self.assertIn("double_bottom", captured[0])

    def test_exit_decision_includes_pattern(self):
        captured = []
        self.oa.ask_openai = lambda prompt, **k: (captured.append(prompt) or '{}')
        pos = {"units":"1","average_price":"1"}
        candles = [{"o":1,"h":2,"l":0.5,"c":1.5}]
        self.oa.get_exit_decision({}, pos, indicators_m1={}, candles=candles, patterns=["double_bottom"])
        self.assertTrue(captured)
        self.assertIn("double_bottom", captured[0])

if __name__ == '__main__':
    unittest.main()
