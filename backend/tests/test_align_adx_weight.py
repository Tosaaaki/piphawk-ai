import importlib
import os
import unittest


class FakeSeries:
    def __init__(self, data=None):
        self._data = list(data or [])
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


class TestAlignAdxWeight(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["ALIGN_ADX_WEIGHT"] = "1"
        os.environ["MIN_ALIGN_ADX"] = "10"
        os.environ["TF_EMA_WEIGHTS"] = "M5:1.0"
        import analysis.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf

    def tearDown(self):
        os.environ.pop("ALIGN_ADX_WEIGHT", None)
        os.environ.pop("MIN_ALIGN_ADX", None)
        os.environ.pop("TF_EMA_WEIGHTS", None)

    def test_adx_direction_applied(self):
        indicators = {
            "M5": {
                "ema_fast": FakeSeries([1.0, 1.0]),
                "ema_slow": FakeSeries([1.0, 1.0]),
                "adx": FakeSeries([15, 22]),
                "plus_di": FakeSeries([30, 35]),
                "minus_di": FakeSeries([20, 15]),
            }
        }
        res = self.sf.is_multi_tf_aligned(indicators, ai_side=None)
        self.assertEqual(res, "long")


if __name__ == "__main__":
    unittest.main()
