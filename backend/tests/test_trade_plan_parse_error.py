import os
import sys
import types
import importlib
import unittest

class TestTradePlanParseError(unittest.TestCase):
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
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def test_parse_error_returns_raw(self):
        self.oa.ask_openai = lambda *a, **k: "invalid-json"
        result = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []})
        self.assertEqual(result.get("entry", {}).get("side"), "no")
        self.assertEqual(result.get("raw"), "invalid-json")

if __name__ == "__main__":
    unittest.main()
