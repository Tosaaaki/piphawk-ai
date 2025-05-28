import os
import sys
import types
import importlib
import unittest


class TestMarketConditionBreak(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LOCAL_WEIGHT_THRESHOLD"] = "0.6"
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
        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {"market_condition": "range"}
        oc.AI_MODEL = "gpt"
        add_module("backend.utils.openai_client", oc)

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        oa.detect_range_break = lambda candles, pivot=None: {"break": True, "direction": "up"}
        oa.classify_breakout = lambda indicators: "range"
        self.oa = oa

    def tearDown(self):
        for name in self._added_modules:
            sys.modules.pop(name, None)

    def test_returns_break_direction(self):
        ctx = {"indicators": {"adx": [30]}, "candles_m5": [{"mid": {"h": "1", "l": "0", "c": "1"}}]}
        res = self.oa.get_market_condition(ctx)
        self.assertEqual(res["market_condition"], "break")
        self.assertEqual(res["break_direction"], "up")


if __name__ == "__main__":
    unittest.main()
