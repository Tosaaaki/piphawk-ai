import os
import tempfile
import unittest
from config import params_loader

class TestParamsLoaderScalp(unittest.TestCase):
    def test_scalp_keys_loaded(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.yml')
        tmp.write(b'SCALP_MODE: true\nSCALP_ADX_MIN: 35\n')
        tmp.close()
        try:
            params_loader.load_params(path=tmp.name, strategy_path=None, settings_path=None)
            self.assertEqual(os.environ.get("SCALP_MODE"), "True")
            self.assertEqual(os.environ.get("SCALP_ADX_MIN"), "35")
        finally:
            os.unlink(tmp.name)
            os.environ.pop("SCALP_MODE", None)
            os.environ.pop("SCALP_ADX_MIN", None)

if __name__ == "__main__":
    unittest.main()
