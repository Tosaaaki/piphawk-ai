import os
import sys
import types
import importlib
import unittest

class TestPatternAIDetection(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._added = []

        def add_module(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added.append(name)

        # Stub openai with minimal client
        response = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"pattern": "double_bottom"}'))]
        )
        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                self.chat = types.SimpleNamespace(
                    completions=types.SimpleNamespace(create=lambda *a, **k: response)
                )
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add_module("openai", openai_stub)

        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add_module("dotenv", dotenv_stub)
        add_module("requests", types.ModuleType("requests"))
        add_module("numpy", types.ModuleType("numpy"))

        import backend.utils.openai_client as oc
        importlib.reload(oc)
        import backend.strategy.pattern_ai_detection as pad
        importlib.reload(pad)
        self.pad = pad

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def test_detect_chart_pattern(self):
        candles = [{"o": 1, "h": 2, "l": 0.5, "c": 1.5}]
        result = self.pad.detect_chart_pattern(candles, ["double_bottom", "double_top"])
        self.assertEqual(result, {"pattern": "double_bottom"})

if __name__ == "__main__":
    unittest.main()
