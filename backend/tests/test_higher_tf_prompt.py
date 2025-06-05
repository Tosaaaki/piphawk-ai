import os
import sys
import types
import importlib
import unittest

class TestHigherTFPrompt(unittest.TestCase):
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

    def tearDown(self):
        for name in getattr(self, "_mods", []):
            sys.modules.pop(name, None)

    def test_prompt_contains_higher_tf_direction(self):
        captured = []
        self.oa.ask_openai = lambda prompt, **k: (captured.append(prompt) or '{"entry": {"side": "no"}}')
        self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []}, higher_tf_direction="long")
        self.assertTrue(captured)
        # プロンプトに Higher Timeframe Direction ラベルが含まれることを確認
        self.assertIn("Higher Timeframe Direction", captured[0])
        self.assertIn("long", captured[0])

if __name__ == "__main__":
    unittest.main()
