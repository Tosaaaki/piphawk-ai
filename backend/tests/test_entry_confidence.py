import importlib
import os
import sys
import types
import unittest


class TestEntryConfidence(unittest.TestCase):
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

    def test_confidence_adjusted_on_conflict(self):
        self.oa.ask_openai = lambda *a, **k: {
            "entry": {"side": "long"},
            "entry_confidence": 0.8,
            "risk": {}
        }
        plan = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []}, higher_tf_direction="short")
        self.assertAlmostEqual(plan.get("entry_confidence"), 0.5)

    def test_confidence_unchanged_when_aligned(self):
        self.oa.ask_openai = lambda *a, **k: {
            "entry": {"side": "short"},
            "entry_confidence": 0.6,
            "risk": {}
        }
        plan = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []}, higher_tf_direction="short")
        self.assertAlmostEqual(plan.get("entry_confidence"), 0.6)

if __name__ == "__main__":
    unittest.main()
