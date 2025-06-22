import importlib
import unittest


class DummyCursor:
    def __init__(self):
        self.params = None

    def execute(self, sql, params=None):
        self.params = params


class DummyConn:
    def __init__(self):
        self.cur = DummyCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def close(self):
        pass


class TestPolicyTransitionLogging(unittest.TestCase):
    def test_transition_written(self):
        conn = DummyConn()
        log_mod = importlib.import_module("backend.logs.log_manager")
        log_mod.get_db_connection = lambda: conn
        log_mod.init_db = lambda: None

        log_mod.log_policy_transition("state", "act", 1.0)

        params = conn.cur.params
        self.assertIsNotNone(params)
        self.assertEqual(params[1], "state")
        self.assertEqual(params[2], "act")
        self.assertEqual(params[3], 1.0)


if __name__ == "__main__":
    unittest.main()
