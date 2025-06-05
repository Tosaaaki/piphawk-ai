import os
import sys
import types
import importlib
import unittest
from datetime import datetime, timezone

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

class TestBeVolatilitySL(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        pandas_stub = types.ModuleType('pandas')
        pandas_stub.Series = FakeSeries
        add('pandas', pandas_stub)
        add('requests', types.ModuleType('requests'))
        add('numpy', types.ModuleType('numpy'))
        dotenv_stub = types.ModuleType('dotenv')
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv_stub)

        openai_stub = types.ModuleType('openai')
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add('openai', openai_stub)
        oc = types.ModuleType('backend.utils.openai_client')
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = 'gpt'
        add('backend.utils.openai_client', oc)

        oa = types.ModuleType('backend.strategy.openai_analysis')
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {'entry': {'side': 'no'}, 'risk': {}}
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(action='HOLD', confidence=0.0, reason='')
        oa.EXIT_BIAS_FACTOR = 1.0
        add('backend.strategy.openai_analysis', oa)

        om = types.ModuleType('backend.orders.order_manager')
        class DummyMgr:
            def __init__(self):
                self.sl_calls = []
            def update_trade_sl(self, trade_id, instrument, price):
                self.sl_calls.append((trade_id, instrument, price))
                return {}
            def enter_trade(self, *a, **k):
                return {}
            def cancel_order(self, *a, **k):
                pass
            def place_market_order(self, *a, **k):
                pass
            def close_position(self, *a, **k):
                pass
        om.OrderManager = DummyMgr
        add('backend.orders.order_manager', om)

        upd = types.ModuleType('backend.logs.update_oanda_trades')
        upd.update_oanda_trades = lambda *a, **k: (_ for _ in ()).throw(SystemExit())
        upd.fetch_trade_details = lambda *a, **k: {}
        add('backend.logs.update_oanda_trades', upd)

        import time
        self._orig_sleep = time.sleep
        time.sleep = lambda *_a, **_k: None

        stub_names = [
            'backend.market_data.tick_fetcher',
            'backend.market_data.candle_fetcher',
            'backend.indicators.calculate_indicators',
            'backend.strategy.exit_logic',
            'backend.orders.position_manager',
            'backend.strategy.signal_filter',
            'backend.strategy.higher_tf_analysis',
            'backend.utils.notification',
            'backend.strategy.pattern_scanner',
        ]
        for name in stub_names:
            mod = types.ModuleType(name)
            add(name, mod)

        sys.modules['backend.market_data.tick_fetcher'].fetch_tick_data = lambda *a, **k: {
            'prices': [{'bids': [{'price': '1.06'}], 'asks': [{'price': '1.07'}], 'tradeable': True}]
        }
        sys.modules['backend.market_data.candle_fetcher'].fetch_multiple_timeframes = lambda *a, **k: {'M5': [], 'M1': [], 'H1': [], 'H4': [], 'D': []}
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators = lambda *a, **k: {}
        def calc_multi(*a, **k):
            return {'M5': {'atr': FakeSeries([0.04]), 'adx': FakeSeries([40])}, 'M1': {}, 'H1': {}, 'H4': {}, 'D': {}}
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators_multi = calc_multi
        sys.modules['backend.strategy.exit_logic'].process_exit = lambda *a, **k: None
        now_str = datetime.now(timezone.utc).isoformat() + 'Z'
        sys.modules['backend.orders.position_manager'].check_current_position = lambda *a, **k: {
            'instrument': 'USD_JPY',
            'long': {'units': '1', 'averagePrice': '1.00', 'tradeIDs': ['t1']},
            'entry_time': now_str
        }
        sys.modules['backend.strategy.signal_filter'].pass_entry_filter = lambda *a, **k: True
        sys.modules['backend.strategy.signal_filter'].pass_exit_filter = lambda *a, **k: True
        sys.modules['backend.strategy.higher_tf_analysis'].analyze_higher_tf = lambda *a, **k: {}
        sys.modules['backend.utils.notification'].send_line_message = lambda *a, **k: None
        sys.modules['backend.strategy.pattern_scanner'].scan = lambda *a, **k: {}
        sys.modules['backend.strategy.pattern_scanner'].PATTERN_DIRECTION = {}

        os.environ['PIP_SIZE'] = '0.01'
        os.environ['BE_TRIGGER_PIPS'] = '5'
        os.environ['BE_ATR_TRIGGER_MULT'] = '0'
        os.environ['BE_TRIGGER_R'] = '0'
        os.environ['BE_VOL_ADX_MIN'] = '30'
        os.environ['BE_VOL_SL_MULT'] = '2.0'

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        jr.instrument_is_tradeable = lambda instrument: True
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: None

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)
        for k in ['PIP_SIZE','BE_TRIGGER_PIPS','BE_ATR_TRIGGER_MULT','BE_TRIGGER_R','BE_VOL_ADX_MIN','BE_VOL_SL_MULT']:
            os.environ.pop(k, None)
        import time
        time.sleep = self._orig_sleep

    def test_high_vol_sl_adjustment(self):
        self.jr.order_mgr.sl_calls.clear()
        with self.assertRaises(SystemExit):
            self.runner.run()
        calls = self.jr.order_mgr.sl_calls
        self.assertTrue(calls, 'update_trade_sl not called')
        _, _, price = calls[0]
        self.assertAlmostEqual(price, 0.92)

    def test_normal_vol_sl_breakeven(self):
        sys.modules['backend.indicators.calculate_indicators'].calculate_indicators_multi = (
            lambda *a, **k: {'M5': {'atr': FakeSeries([0.04]), 'adx': FakeSeries([20])}, 'M1': {}, 'H1': {}, 'H4': {}, 'D': {}}
        )
        self.jr.calculate_indicators_multi = sys.modules['backend.indicators.calculate_indicators'].calculate_indicators_multi
        self.runner = self.jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: None
        self.jr.order_mgr.sl_calls.clear()
        with self.assertRaises(SystemExit):
            self.runner.run()
        calls = self.jr.order_mgr.sl_calls
        self.assertTrue(calls, 'update_trade_sl not called')
        _, _, price = calls[0]
        self.assertAlmostEqual(price, 1.0)

if __name__ == '__main__':
    unittest.main()
