import importlib
import os
import sys
import types
import unittest

from backend.utils import price as price_utils


class DummyResponse:
    def __init__(self):
        self.ok = True
        self.status_code = 201
        self.text = ''
    def json(self):
        return {"ok": True}
    def raise_for_status(self):
        pass

class TestPriceFormatting(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        # stub requests
        req = types.ModuleType("requests")
        captured = {}
        def post(url, json=None, headers=None):
            captured['payload'] = json
            return DummyResponse()
        req.post = post
        req.put = lambda *a, **k: DummyResponse()
        req.get = lambda *a, **k: DummyResponse()
        add("requests", req)
        self._captured = captured

        log_stub = types.ModuleType("backend.logs.log_manager")
        log_stub.log_trade = lambda *a, **k: None
        log_stub.log_error = lambda *a, **k: None
        add("backend.logs.log_manager", log_stub)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")

        import backend.orders.order_manager as om
        importlib.reload(om)
        self.order_manager = om.OrderManager()

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_format_price_function(self):
        self.assertEqual(price_utils.format_price("USD_JPY", 143.2504), "143.250")
        self.assertEqual(price_utils.format_price("EUR_USD", 1.234567), "1.23457")

    def test_limit_order_payload_uses_format(self):
        self.order_manager.place_limit_order(
            instrument="USD_JPY",
            units=1000,
            limit_price=143.2509999,
            tp_pips=10,
            sl_pips=5,
            side="long",
        )
        payload = self._captured.get('payload', {})
        self.assertEqual(payload["order"]["price"], "143.251")
        self.assertEqual(payload["order"]["takeProfitOnFill"]["price"], "143.351")
        self.assertEqual(payload["order"]["stopLossOnFill"]["price"], "143.201")


if __name__ == "__main__":
    unittest.main()
