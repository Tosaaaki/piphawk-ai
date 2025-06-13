import importlib
import unittest


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

class TestEntrySkipLogging(unittest.TestCase):
    def setUp(self):
        conn = DummyConn()
        log_mod = importlib.import_module('backend.logs.log_manager')
        log_mod.get_db_connection = lambda: conn
        self.conn = conn

    def test_skip_logged(self):
        from backend.logs.log_manager import log_entry_skip
        log_entry_skip('EUR_USD', 'long', 'cooldown', 'test')
        self.assertIsNotNone(self.conn.params)
        self.assertEqual(self.conn.params[2], 'long')
        self.assertEqual(self.conn.params[3], 'cooldown')

if __name__ == '__main__':
    unittest.main()
