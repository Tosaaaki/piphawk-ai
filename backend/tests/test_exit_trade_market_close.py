import unittest
import types
import sys
import importlib


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = ""

    def json(self):
        return self._json_data

    @property
    def ok(self):
        return self.status_code == 200

    def raise_for_status(self):
        pass


class TestExitTradeMarketClose(unittest.TestCase):
    def setUp(self):
        self.added = []

        def add(name, mod):
            sys.modules[name] = mod
            self.added.append(name)

        add("pandas", types.ModuleType("pandas"))
        add("numpy", types.ModuleType("numpy"))
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv)
        self.put_calls = []
        self.get_calls = []
        req = types.ModuleType("requests")

        def get(url, headers=None, timeout=10):
            self.get_calls.append(url)
            if url.endswith("/positions/EUR_USD"):
                return DummyResponse(
                    200,
                    {
                        "position": {
                            "long": {"units": "1", "averagePrice": "1.10"},
                            "short": {"units": "0"},
                        }
                    },
                )
            return DummyResponse(200, {})

        def put(url, json=None, headers=None):
            self.put_calls.append(url)
            return DummyResponse(200, {})

        req.get = get
        req.put = put
        add("requests", req)
        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        log_mod.log_error = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)
        import backend.orders.order_manager as om

        importlib.reload(om)
        self.om = om.OrderManager()

    def tearDown(self):
        for n in self.added:
            sys.modules.pop(n, None)

    def test_close_without_cancel(self):
        position = {
            "instrument": "EUR_USD",
            "units": "1",
            "long": {"units": "1", "averagePrice": "1.10", "tradeIDs": ["t1"]},
            "short": {"units": "0"},
        }
        self.om.exit_trade(position)
        self.assertEqual(len(self.put_calls), 1)
        self.assertTrue(self.put_calls[0].endswith("/positions/EUR_USD/close"))


if __name__ == "__main__":
    unittest.main()
