import os
import sys
import types
import importlib
import unittest

class TestCompositeThreshold(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["COMPOSITE_MIN"] = "0.7"
        self._mods = []

        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._mods.append(name)

        pandas_stub = types.ModuleType("pandas")
        add("pandas", pandas_stub)
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
        adx_mod = types.ModuleType("backend.indicators.adx")
        adx_mod.calculate_adx_bb_score = lambda *a, **k: 0.6
        add("backend.indicators.adx", adx_mod)
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_mods", []):
            sys.modules.pop(name, None)
        os.environ.pop("COMPOSITE_MIN", None)

    def test_composite_score_blocks_entry(self):
        self.oa.ask_openai = lambda *a, **k: {"entry": {"side": "long"}, "risk": {}}
        indicators = {"M5": {"adx": [20], "bb_upper": [1.1], "bb_lower": [1.0]}}
        result = self.oa.get_trade_plan({}, indicators, {"M5": []})
        self.assertEqual(result.get("entry", {}).get("side"), "no")

if __name__ == "__main__":
    unittest.main()
