import os
import sys
import types
import importlib
import unittest

class TestGetAICooldownSec(unittest.TestCase):
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

    def test_nested_units_long_or_short(self):
        self.assertEqual(
            self.oa.get_ai_cooldown_sec({"long": {"units": "1"}}),
            self.oa.AI_COOLDOWN_SEC_FLAT,
        )
        self.assertEqual(
            self.oa.get_ai_cooldown_sec({"short": {"units": "-2"}}),
            self.oa.AI_COOLDOWN_SEC_FLAT,
        )

if __name__ == "__main__":
    unittest.main()
