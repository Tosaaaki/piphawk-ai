import importlib
import os
import sys
import types
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

class TestAdjustTpSl(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        req = types.ModuleType("requests")
        self.sent = []
        def put(url, json=None, headers=None):
            self.sent.append(json)
            return DummyResponse(status_code=200, json_data={"ok": True})
        def post(url, json=None, headers=None):
            self.sent.append(json)
            return DummyResponse(status_code=201, json_data={"ok": True})
        req.put = put
        req.post = post
        req.Session = lambda: types.SimpleNamespace()
        req.get = lambda *a, **k: DummyResponse()
        add("requests", req)

        log_stub = types.ModuleType("backend.logs.log_manager")
        self.log_calls = []
        log_stub.log_trade = lambda *a, **k: None
        log_stub.add_trade_label = lambda *a, **k: None
        def log_error(module, code, message=None):
            self.log_calls.append((code, message))
        log_stub.log_error = log_error
        log_stub.log_policy_transition = lambda *a, **k: None
        add("backend.logs.log_manager", log_stub)

        uot_stub = types.ModuleType("backend.logs.update_oanda_trades")
        uot_stub.fetch_trade_details = lambda *_a, **_k: {"trade": {"state": "OPEN", "averagePrice": "0"}}
        add("backend.logs.update_oanda_trades", uot_stub)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")

        import backend.orders.order_manager as om
        importlib.reload(om)
        self.om = om.OrderManager()
        self.om._request_with_retries = lambda method, url, **kw: getattr(req, method)(url, **kw)
        self.om.get_current_tp = lambda *_a, **_k: None

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_post_payload_for_tp(self):
        res = self.om.adjust_tp_sl("USD_JPY", "t1", new_tp=150.0)
        self.assertEqual(res, {"tp": {"ok": True}})
        body = self.sent[0]
        self.assertEqual(body["order"]["type"], "TAKE_PROFIT")

    def test_comment_contains_uuid(self):
        res = self.om.adjust_tp_sl(
            "USD_JPY",
            "t1",
            new_tp=150.0,
            entry_uuid="abc123",
        )
        self.assertEqual(res, {"tp": {"ok": True}})
        body = self.sent[0]
        self.assertEqual(body["order"]["clientExtensions"]["comment"], "abc123")

    def test_error_logging_on_failure(self):
        def fail_post(url, json=None, headers=None):
            return DummyResponse(
                status_code=400,
                json_data={"errorCode": "ERR", "errorMessage": "bad"},
                text='bad'
            )
        sys.modules['requests'].post = fail_post
        res = self.om.adjust_tp_sl("USD_JPY", "t1", new_tp=150.0)
        self.assertIsNone(res)
        self.assertEqual(self.log_calls, [("TP adjustment failed: ERR bad", "bad")])

    def test_put_payload_for_sl(self):
        res = self.om.adjust_tp_sl("USD_JPY", "t1", new_sl=149.0)
        self.assertEqual(res, {"sl": {"ok": True}})
        body = self.sent[0]
        self.assertIn("stopLoss", body)
        self.assertEqual(body["stopLoss"]["price"], "149.000")

if __name__ == '__main__':
    unittest.main()
