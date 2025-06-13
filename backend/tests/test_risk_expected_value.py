import importlib
import os
import sys
import types
import unittest


class TestRiskExpectedValue(unittest.TestCase):
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
        req_stub = types.ModuleType("requests")
        req_stub.Session = lambda: types.SimpleNamespace(request=lambda *a, **k: types.SimpleNamespace(status_code=200))
        req_stub.RequestException = Exception
        req_stub.Response = types.SimpleNamespace
        add("requests", req_stub)
        add("httpx", types.ModuleType("httpx"))
        add("strategies", types.ModuleType("strategies"))
        add("numpy", types.ModuleType("numpy"))
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def test_negative_expected_value(self):
        resp = {"entry": {"side": "long"}, "risk": {"tp_pips": 10, "sl_pips": 40.5, "tp_prob": 0.8, "sl_prob": 0.5}}
        self.oa.ask_model = lambda *a, **k: resp
        plan = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []})
        self.assertEqual(plan.get("entry", {}).get("side"), "no")
        self.assertEqual(plan.get("risk"), {})

if __name__ == "__main__":
    unittest.main()
