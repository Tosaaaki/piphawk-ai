import os
import sys
import types
import importlib
import unittest

class TestExitPipsSymmetry(unittest.TestCase):
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
        self.oa._last_exit_ai_call_time = 0.0

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def _capture_pips(self, market_data, pos):
        captured = []
        self.oa.ask_openai = lambda prompt, **k: (captured.append(prompt) or {})
        self.oa._last_exit_ai_call_time = 0.0
        self.oa.get_exit_decision(market_data, pos, indicators_m1={})
        self.assertTrue(captured)
        for line in captured[0].splitlines():
            if line.startswith("- Pips From Entry:"):
                return float(line.split(":")[1].strip())
        return None

    def test_long_short_equal_pips(self):
        long_pips = self._capture_pips(
            {"bid": 1.12, "ask": 1.13},
            {"units": "1", "average_price": "1.10"},
        )
        short_pips = self._capture_pips(
            {"bid": 1.09, "ask": 1.08},
            {"units": "-1", "average_price": "1.10"},
        )
        self.assertAlmostEqual(long_pips, short_pips, places=6)

if __name__ == "__main__":
    unittest.main()
