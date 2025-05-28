import os
import sys
import types
import importlib
import unittest
from datetime import datetime

class TestMinHoldExit(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        os.environ['MIN_HOLD_SEC'] = '60'
        os.environ['AI_PROFIT_TRIGGER_RATIO'] = '0'
        os.environ['PIP_SIZE'] = '0.0001'
        os.environ.pop('OANDA_API_KEY', None)
        os.environ.pop('OANDA_ACCOUNT_ID', None)

        add('pandas', types.ModuleType('pandas'))
        add('requests', types.ModuleType('requests'))
        add('numpy', types.ModuleType('numpy'))
        dotenv = types.ModuleType('dotenv')
        dotenv.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv)

        oa = types.ModuleType('backend.strategy.openai_analysis')
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {'entry': {'side': 'long'}, 'risk': {}}
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(action='HOLD', confidence=0.0, reason='')
        oa.EXIT_BIAS_FACTOR = 1.0
        add('backend.strategy.openai_analysis', oa)

        om = types.ModuleType('backend.orders.order_manager')
        class DummyMgr:
            def __init__(self):
                self.calls = []
            def update_trade_sl(self, *a, **k):
                return {}
            def enter_trade(self, *a, **k):
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
            'prices': [{'bids': [{'price': '1.005'}], 'asks': [{'price': '1.006'}]}]
        }
        sys.modules['backend.market_data.candle_fetcher'].fetch_multiple_timeframes = lambda *a, **k: {'M5': [], 'M1': [], 'H1': [], 'H4': [], 'D': []}
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators = lambda *a, **k: {}
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators_multi = lambda *a, **k: {'M5': {}, 'M1': {}, 'H1': {}, 'H4': {}, 'D': {}}
        self.exit_called = []
        sys.modules['backend.strategy.exit_logic'].process_exit = lambda *a, **k: self.exit_called.append(True)
        now_str = datetime.utcnow().isoformat() + 'Z'
        sys.modules['backend.orders.position_manager'].check_current_position = lambda *a, **k: {
            'instrument': 'EUR_USD',
            'long': {'units': '1', 'averagePrice': '1.0000', 'tradeIDs': ['t1']},
            'entry_time': now_str
        }
        sys.modules['backend.strategy.signal_filter'].pass_entry_filter = lambda *a, **k: True
        sys.modules['backend.strategy.signal_filter'].pass_exit_filter = lambda *a, **k: True
        sys.modules['backend.strategy.higher_tf_analysis'].analyze_higher_tf = lambda *a, **k: {}
        sys.modules['backend.utils.notification'].send_line_message = lambda *a, **k: None

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: None

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)
        os.environ.pop('MIN_HOLD_SEC', None)
        os.environ.pop('AI_PROFIT_TRIGGER_RATIO', None)
        os.environ.pop('PIP_SIZE', None)

    def test_no_exit_before_min_hold(self):
        with self.assertRaises(SystemExit):
            self.runner.run()
        self.assertEqual(self.exit_called, [])

if __name__ == '__main__':
    unittest.main()

