import os
import sys
import types
import importlib
import unittest

class TestProbValidation(unittest.TestCase):
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
        os.environ.pop("MIN_TP_PROB", None)
        os.environ.pop("PROB_MARGIN", None)

    def test_sum_within_margin(self):
        os.environ["MIN_TP_PROB"] = "0.5"
        os.environ["PROB_MARGIN"] = "0.02"
        import importlib
        importlib.reload(self.oa)
        self.oa.ask_openai = lambda *a, **k: {
            "entry": {"side": "long"},
            "risk": {"tp_pips": 10, "sl_pips": 5, "tp_prob": 0.51, "sl_prob": 0.51},
        }
        result = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []})
        self.assertEqual(result.get("entry", {}).get("side"), "long")

    def test_prob_clamped(self):
        os.environ["MIN_TP_PROB"] = "0.5"
        os.environ["PROB_MARGIN"] = "0.02"
        import importlib
        importlib.reload(self.oa)
        self.oa.ask_openai = lambda *a, **k: {
            "entry": {"side": "long"},
            "risk": {"tp_pips": 10, "sl_pips": 5, "tp_prob": 1.5, "sl_prob": -0.2},
        }
        result = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []})
        risk = result.get("risk", {})
        self.assertEqual(risk.get("tp_prob"), 1.0)
        self.assertEqual(risk.get("sl_prob"), 0.0)
        self.assertEqual(result.get("entry", {}).get("side"), "long")

    def test_prob_normalized(self):
        os.environ["MIN_TP_PROB"] = "0.5"
        os.environ["PROB_MARGIN"] = "0.02"
        import importlib
        importlib.reload(self.oa)
        self.oa.ask_openai = lambda *a, **k: {
            "entry": {"side": "long"},
            "risk": {"tp_pips": 10, "sl_pips": 5, "tp_prob": 0.6, "sl_prob": 0.44},
        }
        result = self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []})
        risk = result.get("risk", {})
        self.assertAlmostEqual(risk.get("tp_prob", 0) + risk.get("sl_prob", 0), 1.0)
        self.assertEqual(result.get("entry", {}).get("side"), "long")

if __name__ == "__main__":
    unittest.main()
