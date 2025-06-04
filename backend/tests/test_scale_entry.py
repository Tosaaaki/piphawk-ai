import os
import sys
import types
import importlib
import unittest
from datetime import datetime

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

class TestScaleEntry(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        os.environ['SCALE_LOT_SIZE'] = '0.7'
        os.environ['AI_PROFIT_TRIGGER_RATIO'] = '0'
        os.environ['PIP_SIZE'] = '0.01'
        os.environ.pop('OANDA_API_KEY', None)
        os.environ.pop('OANDA_ACCOUNT_ID', None)

        pandas_stub = types.ModuleType('pandas')
        pandas_stub.Series = FakeSeries
        add('pandas', pandas_stub)
        add('requests', types.ModuleType('requests'))
        add('numpy', types.ModuleType('numpy'))
        dotenv_stub = types.ModuleType('dotenv')
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv_stub)

        ead = types.ModuleType('backend.strategy.exit_ai_decision')
        ead.evaluate = lambda *a, **k: types.SimpleNamespace(action='SCALE', confidence=0.9, reason='')
        add('backend.strategy.exit_ai_decision', ead)

        oa = types.ModuleType('backend.strategy.openai_analysis')
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {'entry': {'side': 'no'}, 'risk': {}}
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = ead.evaluate
        oa.EXIT_BIAS_FACTOR = 1.0
        add('backend.strategy.openai_analysis', oa)

        om = types.ModuleType('backend.orders.order_manager')
        class DummyMgr:
            def __init__(self):
                self.calls = []
            def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False, with_oco=True):
                self.calls.append((side, lot_size, strategy_params))
                return {'order_id': '1'}
            def update_trade_sl(self, *a, **k):
                return {}
            def cancel_order(self, *a, **k):
                pass
            def place_market_order(self, *a, **k):
                pass
        om.OrderManager = DummyMgr
        add('backend.orders.order_manager', om)

        upd = types.ModuleType('backend.logs.update_oanda_trades')
        upd.update_oanda_trades = lambda *a, **k: (_ for _ in ()).throw(SystemExit())
        upd.fetch_trade_details = lambda *a, **k: {}
        add('backend.logs.update_oanda_trades', upd)

        stub_names = [
            'backend.market_data.tick_fetcher',
            'backend.market_data.candle_fetcher',
            'backend.indicators.calculate_indicators',
            'backend.strategy.exit_logic',
            'backend.orders.position_manager',
            'backend.strategy.signal_filter',
            'backend.strategy.higher_tf_analysis',
            'backend.utils.notification',
        ]
        for name in stub_names:
            mod = types.ModuleType(name)
            add(name, mod)

        sys.modules['backend.market_data.tick_fetcher'].fetch_tick_data = lambda *a, **k: {
            'prices': [{'bids': [{'price': '1.0'}], 'asks': [{'price': '1.01'}], 'tradeable': True}]
        }
        sys.modules['backend.market_data.candle_fetcher'].fetch_multiple_timeframes = lambda *a, **k: {'M5': [], 'M1': [], 'H1': [], 'H4': [], 'D': []}
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators = lambda *a, **k: {'atr': FakeSeries([0.1]), 'rsi': FakeSeries([50]), 'ema_slope': FakeSeries([0.1])}
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators_multi = lambda *a, **k: {
            'M5': {'atr': FakeSeries([0.1]), 'rsi': FakeSeries([50]), 'ema_slope': FakeSeries([0.1])},
            'M1': {}, 'H1': {}, 'H4': {}, 'D': {}
        }
        sys.modules['backend.strategy.exit_logic'].process_exit = lambda *a, **k: False
        now_str = datetime.utcnow().isoformat() + 'Z'
        sys.modules['backend.orders.position_manager'].check_current_position = lambda *a, **k: {
            'instrument': 'USD_JPY',
            'long': {'units': '1', 'averagePrice': '1.0000', 'tradeIDs': ['t1']},
            'entry_time': now_str
        }
        sys.modules['backend.orders.position_manager'].get_margin_used = lambda *a, **k: 0
        sys.modules['backend.strategy.signal_filter'].pass_entry_filter = lambda *a, **k: True
        sys.modules['backend.strategy.signal_filter'].pass_exit_filter = lambda *a, **k: True
        sys.modules['backend.strategy.higher_tf_analysis'].analyze_higher_tf = lambda *a, **k: {}
        sys.modules['backend.utils.notification'].send_line_message = lambda *a, **k: None

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        jr.instrument_is_tradeable = lambda instrument: True
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: None

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)
        os.environ.pop('SCALE_LOT_SIZE', None)
        os.environ.pop('AI_PROFIT_TRIGGER_RATIO', None)
        os.environ.pop('PIP_SIZE', None)

    def test_scale_order_sent(self):
        with self.assertRaises(SystemExit):
            self.runner.run()
        calls = self.runner.order_mgr.calls
        self.assertEqual(len(calls), 1)
        side, lot, params = calls[0]
        self.assertEqual(side, 'long')
        self.assertAlmostEqual(lot, 0.7)
        self.assertEqual(params['instrument'], 'USD_JPY')

if __name__ == '__main__':
    unittest.main()
