import os
import sys
import types
import importlib
import unittest


class TestLLMExitAdjustment(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._mods = []

        def add(name: str, mod: types.ModuleType):
            sys.modules[name] = mod
            self._mods.append(name)

        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: "{}"
        oc.AI_MODEL = "gpt"
        oc.set_call_limit = lambda *_a, **_k: None
        add("backend.utils.openai_client", oc)

        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_ai_decision = lambda *a, **k: None
        log_mod.log_prompt_response = lambda *a, **k: None
        log_mod.log_exit_adjust = lambda *a, **k: None
        log_mod.count_exit_adjust_calls = lambda *_a, **_k: 0
        add("backend.logs.log_manager", log_mod)

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        os.environ.pop("OPENAI_API_KEY", None)

    def test_parse_error_fallback(self):
        sys.modules["backend.utils.openai_client"].ask_openai = lambda *a, **k: "{"
        import backend.strategy.llm_exit as le
        importlib.reload(le)
        res = le.propose_exit_adjustment({"instrument": "USD_JPY"})
        self.assertEqual(res, {"action": "HOLD", "tp": None, "sl": None})

    def test_parse_success(self):
        sys.modules["backend.utils.openai_client"].ask_openai = lambda *a, **k: {"action": "REDUCE_TP", "tp": 1.05, "sl": None}
        import backend.strategy.llm_exit as le
        importlib.reload(le)
        res = le.propose_exit_adjustment({"instrument": "USD_JPY"})
        self.assertEqual(res["action"], "REDUCE_TP")
        self.assertAlmostEqual(res["tp"], 1.05)
        self.assertIsNone(res["sl"])


if __name__ == "__main__":
    unittest.main()
