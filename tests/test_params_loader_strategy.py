import os
import tempfile
import unittest

from config import params_loader


class TestParamsLoaderStrategy(unittest.TestCase):
    def test_strategy_aliases(self):
        yml = b"""\nrisk:\n  min_atr_sl_multiplier: 1.1\n  min_rr_ratio: 1.5\nfilters:\n  avoid_false_break:\n    lookback_candles: 10\n    threshold_ratio: 0.4\nreentry:\n  trigger_pips_over_break: 1.2\n"""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.yml')
        tmp.write(yml)
        tmp.close()
        try:
            params_loader.load_params(path=tmp.name, strategy_path=None, settings_path=None)
            self.assertEqual(os.environ.get('MIN_ATR_MULT'), '1.1')
            self.assertEqual(os.environ.get('MIN_RRR'), '1.5')
            self.assertEqual(os.environ.get('FALSE_BREAK_LOOKBACK'), '10')
            self.assertEqual(os.environ.get('FALSE_BREAK_RATIO'), '0.4')
            self.assertEqual(os.environ.get('REENTRY_TRIGGER_PIPS'), '1.2')
        finally:
            os.unlink(tmp.name)
            for k in ['MIN_ATR_MULT','MIN_RRR','FALSE_BREAK_LOOKBACK','FALSE_BREAK_RATIO','REENTRY_TRIGGER_PIPS']:
                os.environ.pop(k, None)

if __name__ == '__main__':
    unittest.main()
