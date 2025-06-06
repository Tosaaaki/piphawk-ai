import os
import tempfile
import unittest
from config import params_loader

class TestParamsLoaderMode(unittest.TestCase):
    def test_mode_keys_loaded(self):
        yml = "trend_score_min: 5\nweights:\n  adx_m5: 3\n"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.yml')
        tmp.write(yml.encode())
        tmp.close()
        try:
            params_loader.load_params(mode_path=tmp.name, path=None, strategy_path=None, settings_path=None)
            self.assertEqual(os.environ.get('TREND_SCORE_MIN'), '5')
            self.assertEqual(os.environ.get('WEIGHTS_ADX_M5'), '3')
        finally:
            os.unlink(tmp.name)
            os.environ.pop('TREND_SCORE_MIN', None)
            os.environ.pop('WEIGHTS_ADX_M5', None)

if __name__ == '__main__':
    unittest.main()
