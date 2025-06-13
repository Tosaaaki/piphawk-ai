import importlib
import os
import sys
import types
import unittest


class DummyConn:
    def __init__(self):
        self.executed = []
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def cursor(self):
        return self
    def execute(self, sql, params=None):
        self.executed.append((sql, params))
    def commit(self):
        pass
    def close(self):
        pass

class TestAIDecisionLogging(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self.added = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self.added.append(name)
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
        conn = DummyConn()
        log_mod = importlib.import_module("backend.logs.log_manager")
        log_mod.get_db_connection = lambda: conn
        self.conn = conn
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa
        self.oa.ask_openai = lambda *a, **k: {"entry": {"side": "long"}, "risk": {}}

    def tearDown(self):
        for name in self.added:
            sys.modules.pop(name, None)
        os.environ.pop("OPENAI_API_KEY", None)

    def test_row_inserted(self):
        self.oa.get_trade_plan({}, {"M5": {}}, {"M5": []}, instrument="EUR_USD")
        self.oa.get_exit_decision({}, {"units": "1", "average_price": "1"}, indicators_m1={}, instrument="EUR_USD")
        inserts = [sql for sql, _ in self.conn.executed if "ai_decisions" in sql]
        self.assertEqual(len(inserts), 2)

if __name__ == "__main__":
    unittest.main()
