import unittest
import sys
import types
import importlib

class DummyConn:
    def __init__(self):
        self.params = None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def cursor(self):
        return self
    def execute(self, sql, params=None):
        self.params = params
    def commit(self):
        pass
    def close(self):
        pass

class TestExitReasonLogging(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)
        add('pandas', types.ModuleType('pandas'))
        add('requests', types.ModuleType('requests'))
        add('numpy', types.ModuleType('numpy'))
        dotenv = types.ModuleType('dotenv')
        dotenv.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv)
        conn = DummyConn()
        log_mod = importlib.import_module('backend.logs.log_manager')
        log_mod.get_db_connection = lambda: conn
        self.conn = conn
        import backend.logs.trade_logger as tl
        importlib.reload(tl)
        self.tl = tl

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)

    def test_exit_reason_value_logged(self):
        self.tl.log_trade(
            instrument='EUR_USD',
            entry_time='2024-01-01T00:00:00',
            entry_price=1.0,
            units=1,
            ai_reason='test',
            exit_time='2024-01-01T01:00:00',
            exit_price=1.1,
            exit_reason=self.tl.ExitReason.AI,
        )
        self.assertIsNotNone(self.conn.params)
        # exit_reason is stored before is_manual flag
        self.assertEqual(self.conn.params[-2], 'AI')

if __name__ == '__main__':
    unittest.main()
