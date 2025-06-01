import os
import sys
import types
import importlib
import unittest

class FakeSeries:
    def __init__(self, data):
        self._data = list(data)
        class _ILoc:
            def __init__(self, outer):
                self._outer = outer
            def __getitem__(self, idx):
                return self._outer._data[idx]
        self.iloc = _ILoc(self)
    def __getitem__(self, idx):
        return self._data[idx]
    def __len__(self):
        return len(self._data)

class TestDuplicateEntryPrevention(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        pandas_stub = types.ModuleType('pandas')
        pandas_stub.Series = FakeSeries
        add('pandas', pandas_stub)
        req = types.ModuleType('requests')
        class DummyResp:
            status_code = 200
            text = ''
            def json(self):
                return {'orders': []}
            def raise_for_status(self):
                pass
        req.post = lambda *a, **k: DummyResp()
        req.put = lambda *a, **k: DummyResp()
        req.get = lambda *a, **k: DummyResp()
        add('requests', req)
        add('numpy', types.ModuleType('numpy'))
        dotenv_stub = types.ModuleType('dotenv')
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv_stub)

        oa = types.ModuleType('backend.strategy.openai_analysis')
        oa.get_trade_plan = lambda *a, **k: {
            'entry': {'side': 'long', 'mode': 'market'},
            'risk': {'tp_pips': 10, 'sl_pips': 5}
        }
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(action='HOLD', confidence=0.0, reason='')
        oa.EXIT_BIAS_FACTOR = 1.0
        add('backend.strategy.openai_analysis', oa)

        om = types.ModuleType('backend.orders.order_manager')
        class DummyMgr:
            def __init__(self):
                self.calls = 0
            def enter_trade(self, *a, **k):
                self.calls += 1
                return {'order_id': '1'}
            def get_open_orders(self, instrument, side):
                return [{'id': 'x'}]
        om.OrderManager = DummyMgr
        add('backend.orders.order_manager', om)

        log_stub = types.ModuleType('backend.logs.log_manager')
        log_stub.log_trade = lambda *a, **k: None
        add('backend.logs.log_manager', log_stub)

        dp = types.ModuleType('backend.strategy.dynamic_pullback')
        dp.calculate_dynamic_pullback = lambda *a, **k: 0
        add('backend.strategy.dynamic_pullback', dp)

        os.environ['PIP_SIZE'] = '0.01'
        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el

    def tearDown(self):
        for m in self._mods:
            sys.modules.pop(m, None)
        os.environ.pop('PIP_SIZE', None)

    def test_skip_when_order_exists(self):
        indicators = {'atr': FakeSeries([0.1])}
        candles = []
        market_data = {'prices': [{'instrument': 'USD_JPY', 'bids': [{'price': '1.0'}], 'asks': [{'price': '1.01'}]}]}
        res = self.el.process_entry(indicators, candles, market_data)
        self.assertFalse(res)
        self.assertEqual(self.el.order_manager.calls, 0)

if __name__ == '__main__':
    unittest.main()
