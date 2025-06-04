import os
import sys
import types
import importlib
import unittest

from backend.filters.false_break_filter import should_skip


class TestFalseBreakFilter(unittest.TestCase):
    def _c(self, o, h, l, c):
        return {"mid": {"o": str(o), "h": str(h), "l": str(l), "c": str(c)}}

    def test_should_skip_detects_upper_wick(self):
        candles = [
            self._c(1.00, 1.04, 0.99, 1.02),
            self._c(1.02, 1.05, 1.01, 1.03),
            self._c(1.03, 1.05, 1.02, 1.04),
            self._c(1.04, 1.06, 1.03, 1.05),
            self._c(1.05, 1.06, 1.04, 1.05),
            self._c(1.055, 1.07, 1.04, 1.045),
        ]
        self.assertTrue(should_skip(candles, lookback=5, threshold_ratio=0.4))

    def test_should_skip_false_when_no_reversal(self):
        candles = [
            self._c(1.00, 1.04, 0.99, 1.02),
            self._c(1.02, 1.05, 1.01, 1.03),
            self._c(1.03, 1.05, 1.02, 1.04),
            self._c(1.04, 1.06, 1.03, 1.05),
            self._c(1.05, 1.06, 1.04, 1.05),
            self._c(1.055, 1.07, 1.05, 1.065),
        ]
        self.assertFalse(should_skip(candles, lookback=5, threshold_ratio=0.4))


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


class TestEntryLogicFalseBreak(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        pandas_stub = types.ModuleType('pandas')
        pandas_stub.Series = FakeSeries
        add('pandas', pandas_stub)
        add('requests', types.ModuleType('requests'))
        dotenv_stub = types.ModuleType('dotenv')
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add('dotenv', dotenv_stub)

        oa = types.ModuleType('backend.strategy.openai_analysis')
        oa.get_trade_plan = lambda *a, **k: {
            'entry': {'side': 'long', 'mode': 'market'},
            'risk': {'tp_pips': 10, 'sl_pips': 5}
        }
        oa.should_convert_limit_to_market = lambda ctx: True
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action='HOLD', confidence=0.0, reason='')
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
                return []
        om.OrderManager = DummyMgr
        add('backend.orders.order_manager', om)

        log_mod = types.ModuleType('backend.logs.log_manager')
        log_mod.log_trade = lambda *a, **k: None
        add('backend.logs.log_manager', log_mod)

        dp = types.ModuleType('backend.strategy.dynamic_pullback')
        dp.calculate_dynamic_pullback = lambda *a, **k: 0
        add('backend.strategy.dynamic_pullback', dp)

        os.environ['PIP_SIZE'] = '0.01'
        os.environ['FALSE_BREAK_LOOKBACK'] = '5'
        os.environ['FALSE_BREAK_RATIO'] = '0.4'

        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el

    def tearDown(self):
        for m in self._mods:
            sys.modules.pop(m, None)
        os.environ.pop('PIP_SIZE', None)
        os.environ.pop('FALSE_BREAK_LOOKBACK', None)
        os.environ.pop('FALSE_BREAK_RATIO', None)

    def _c(self, o, h, l, c):
        return {'mid': {'o': str(o), 'h': str(h), 'l': str(l), 'c': str(c)}}

    def test_entry_skipped_on_false_break(self):
        indicators = {'atr': FakeSeries([0.1])}
        candles = [
            self._c(1.00, 1.04, 0.99, 1.02),
            self._c(1.02, 1.05, 1.01, 1.03),
            self._c(1.03, 1.05, 1.02, 1.04),
            self._c(1.04, 1.06, 1.03, 1.05),
            self._c(1.05, 1.06, 1.04, 1.05),
            self._c(1.055, 1.07, 1.04, 1.045),
        ]
        market_data = {'prices': [{'instrument': 'USD_JPY', 'bids': [{'price': '1.0'}], 'asks': [{'price': '1.01'}]}]}
        res = self.el.process_entry(
            indicators,
            candles,
            market_data,
            candles_dict={'M5': candles},
            tf_align=None,
        )
        self.assertFalse(res)
        self.assertEqual(self.el.order_manager.calls, 0)


if __name__ == '__main__':
    unittest.main()
