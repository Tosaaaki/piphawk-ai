import os
import sys
import types
import importlib
import unittest

class DummyResponse:
    def __init__(self, status_code=201, json_data=None, text=''):
        self.status_code = status_code
        self._json_data = json_data or {"ok": True}
        self.text = text
    def json(self):
        return self._json_data
    def raise_for_status(self):
        pass
    @property
    def ok(self):
        return self.status_code in (200, 201)

class TestEntryRegimeLogging(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        req = types.ModuleType("requests")
        def post(url, json=None, headers=None):
            return DummyResponse()
        req.post = post
        req.put = lambda *a, **k: DummyResponse()
        req.get = lambda *a, **k: DummyResponse()
        add("requests", req)

        log_stub = types.ModuleType("backend.logs.log_manager")
        self.logged = {}
        def log_trade(*args, **kwargs):
            self.logged['entry_regime'] = kwargs.get('entry_regime')
        log_stub.log_trade = log_trade
        log_stub.log_error = lambda *a, **k: None
        add("backend.logs.log_manager", log_stub)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")

        import backend.orders.order_manager as om
        importlib.reload(om)
        self.om = om.OrderManager()

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_entry_regime_logged(self):
        market_data = {
            'prices': [{
                'instrument': 'USD_JPY',
                'bids': [{'price': '1.0'}],
                'asks': [{'price': '1.01'}]
            }]
        }
        params = {
            'instrument': 'USD_JPY',
            'tp_pips': 10,
            'sl_pips': 5,
            'mode': 'market',
            'market_cond': {'market_condition': 'trend'}
        }
        self.om.enter_trade(side='long', lot_size=1.0, market_data=market_data, strategy_params=params)
        self.assertIsNotNone(self.logged.get('entry_regime'))

if __name__ == '__main__':
    unittest.main()
