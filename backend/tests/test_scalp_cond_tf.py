import os
import sys
import types
import importlib
import unittest


class TestScalpCondTf(unittest.TestCase):
    def setUp(self):
        # stub external modules
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)
        add("requests", types.ModuleType("requests"))
        openai_stub = types.ModuleType("openai")
        openai_stub.OpenAI = lambda *a, **k: None
        openai_stub.APIError = Exception
        add("openai", openai_stub)
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = lambda *a, **k: None
        add("pandas", pandas_stub)
        add("numpy", types.ModuleType("numpy"))
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)
        notif_stub = types.ModuleType("backend.utils.notification")
        notif_stub.send_line_message = lambda *a, **k: None
        add("backend.utils.notification", notif_stub)

        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")
        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ["SCALP_MODE"] = "true"
        os.environ["SCALP_COND_TF"] = "M1"

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        self.jr = jr.JobRunner(interval_seconds=1)
        os.environ["SCALP_MODE"] = "true"
        os.environ["SCALP_COND_TF"] = "M1"
        self.jr.indicators_M1 = {"foo": 1}
        self.jr.indicators_M5 = {"foo": 5}
        self.jr.scalp_cond_tf = "M1"

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)
        os.environ.pop("SCALP_MODE", None)
        os.environ.pop("SCALP_COND_TF", None)
        os.environ.pop("OANDA_API_KEY", None)
        os.environ.pop("OANDA_ACCOUNT_ID", None)
        os.environ.pop("OPENAI_API_KEY", None)

    def test_get_cond_indicators_scalp(self):
        os.environ["SCALP_COND_TF"] = "M1"
        self.jr.scalp_cond_tf = "M1"
        self.assertEqual(self.jr._get_cond_indicators(), {"foo": 1})

    def test_get_cond_indicators_s10(self):
        os.environ["SCALP_COND_TF"] = "S10"
        self.jr.indicators_S10 = {"foo": 10}
        self.jr.scalp_cond_tf = "S10"
        self.assertEqual(self.jr._get_cond_indicators(), {"foo": 10})


if __name__ == "__main__":
    unittest.main()
