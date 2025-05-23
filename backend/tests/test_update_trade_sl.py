import os
import sys
import types
import importlib
import unittest

class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=''):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data

    def raise_for_status(self):
        pass

    @property
    def ok(self):
        return self.status_code == 200


class TestUpdateTradeSL(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        # mock requests
        req = types.ModuleType("requests")
        self.captured = {}
        def put(url, json=None, headers=None):
            self.captured['body'] = json
            return DummyResponse(status_code=200, json_data={"ok": True})
        req.put = put
        req.post = lambda *a, **k: DummyResponse()
        req.get = lambda *a, **k: DummyResponse()
        add("requests", req)

        # mock log manager
        log_stub = types.ModuleType("backend.logs.log_manager")
        self.log_calls = []
        log_stub.log_trade = lambda *a, **k: None
        def log_error(module, code, message=None):
            self.log_calls.append((code, message))
        log_stub.log_error = log_error
        add("backend.logs.log_manager", log_stub)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")

        import backend.orders.order_manager as om
        importlib.reload(om)
        self.om = om.OrderManager()

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_payload_contains_stop_loss_type(self):
        self.om.update_trade_sl("t1", "USD_JPY", 150.1234)
        body = self.captured.get('body')
        self.assertIsNotNone(body)
        self.assertEqual(body['order']['type'], 'STOP_LOSS')
        self.assertEqual(body['order']['price'], '150.123')

    def test_error_logging_records_details(self):
        def error_put(url, json=None, headers=None):
            self.captured['body'] = json
            return DummyResponse(
                status_code=400,
                json_data={"errorCode": "ERR", "errorMessage": "bad"},
                text='bad'
            )
        sys.modules['requests'].put = error_put
        self.om.update_trade_sl("t1", "USD_JPY", 150.1234)
        self.assertEqual(self.log_calls, [("ERR", "bad")])


if __name__ == '__main__':
    unittest.main()
