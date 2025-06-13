import importlib
import os
import sys
import types
import unittest


class FakeSeries:
    def __init__(self, val):
        class _IL:
            def __getitem__(self, idx):
                return val
        self.iloc = _IL()
        self._val = val
    def __getitem__(self, idx):
        return self._val
    def __len__(self):
        return 1

class DummyOM:
    def __init__(self):
        self.last_params = None
    def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False, with_oco=True):
        self.last_params = strategy_params
        return {"order_id": "1"}
    def get_open_orders(self, instrument, side):
        return []

class TestFallbackDynamicRisk(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        pandas_stub = types.ModuleType('pandas')
        pandas_stub.Series = FakeSeries
        add('pandas', pandas_stub)
        req_mod = types.ModuleType('requests')
        req_mod.Session = lambda *a, **k: types.SimpleNamespace()
        add('requests', req_mod)
        dotenv_stub = types.ModuleType('dotenv')
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv_stub)

        oa = types.ModuleType('backend.strategy.openai_analysis')
        oa.get_trade_plan = lambda *a, **k: {'entry': {'side': 'no', 'mode': 'market'}, 'risk': {}}
        oa.should_convert_limit_to_market = lambda ctx: True
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action='HOLD', confidence=0.0, reason='')
        oa.EXIT_BIAS_FACTOR = 1.0
        add('backend.strategy.openai_analysis', oa)

        om = types.ModuleType('backend.orders.order_manager')
        om.OrderManager = DummyOM
        add('backend.orders.order_manager', om)

        log_mod = types.ModuleType('backend.logs.log_manager')
        log_mod.log_trade = lambda *a, **k: None
        add('backend.logs.log_manager', log_mod)

        comp = types.ModuleType('piphawk_ai.signals.composite_mode')
        comp.decide_trade_mode = lambda inds: 'trend'
        add('piphawk_ai.signals.composite_mode', comp)

        self.add = add
        os.environ['PIP_SIZE'] = '0.01'
        os.environ['FALLBACK_FORCE_ON_NO_SIDE'] = 'true'
        os.environ['FALLBACK_DEFAULT_SL_PIPS'] = '8'
        os.environ['FALLBACK_DEFAULT_TP_PIPS'] = '12'
        os.environ['ATR_MULT_TP'] = '2'
        os.environ['ATR_MULT_SL'] = '3'
        os.environ['MIN_ATR_MULT'] = '0'
        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el
        self._mods.append('backend.strategy.entry_logic')

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        for k in ['PIP_SIZE','FALLBACK_FORCE_ON_NO_SIDE','FALLBACK_DEFAULT_SL_PIPS','FALLBACK_DEFAULT_TP_PIPS','ATR_MULT_TP','ATR_MULT_SL','MIN_ATR_MULT','FALLBACK_DYNAMIC_RISK']:
            os.environ.pop(k, None)

    def _run_entry(self):
        indicators = {'atr': FakeSeries(0.05)}
        candles = []
        market_data = {'prices': [{'instrument': 'USD_JPY', 'bids': [{'price': '1.0'}], 'asks': [{'price': '1.01'}]}]}
        return self.el.process_entry(indicators, candles, market_data, market_cond={'trend_direction':'long'}, candles_dict={'M5': candles}, tf_align=None)

    def test_fixed_risk(self):
        os.environ['FALLBACK_DYNAMIC_RISK'] = 'false'
        res = self._run_entry()
        self.assertTrue(res)
        self.assertEqual(self.el.order_manager.last_params['sl_pips'], 8.0)
        self.assertEqual(self.el.order_manager.last_params['tp_pips'], 12.0)

    def test_dynamic_risk(self):
        os.environ['FALLBACK_DYNAMIC_RISK'] = 'true'
        res = self._run_entry()
        self.assertTrue(res)
        self.assertAlmostEqual(self.el.order_manager.last_params['tp_pips'], 10.0)
        self.assertAlmostEqual(self.el.order_manager.last_params['sl_pips'], 15.0)

if __name__ == '__main__':
    unittest.main()
