import importlib
import os
import sys
import types
import unittest


class TestExitBiasFactor(unittest.TestCase):
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
        import backend.strategy.exit_ai_decision as ead
        importlib.reload(ead)
        self.ead = ead

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)

    def test_confidence_scaled_by_bias(self):
        self.ead.ask_openai = lambda *a, **k: {"action": "EXIT", "confidence": 0.4, "reason": "test"}
        res_neutral = self.ead.evaluate({"side": "long"}, bias_factor=1.0)
        res_aggressive = self.ead.evaluate({"side": "long"}, bias_factor=2.0)
        self.assertAlmostEqual(res_neutral.confidence, 0.4)
        self.assertAlmostEqual(res_aggressive.confidence, 0.8)

if __name__ == "__main__":
    unittest.main()
