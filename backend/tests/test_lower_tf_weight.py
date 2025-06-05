import os
import importlib
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


class TestLowerTfWeight(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["LT_TF_PRIORITY_ADX"] = "30"
        os.environ["LT_TF_WEIGHT_FACTOR"] = "0.5"
        os.environ["TF_EMA_WEIGHTS"] = "M5:0.6,H1:0.4"
        os.environ["AI_ALIGN_WEIGHT"] = "0"
        os.environ["ALIGN_BYPASS_ADX"] = "0"
        import analysis.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf

    def tearDown(self):
        for k in [
            "LT_TF_PRIORITY_ADX",
            "LT_TF_WEIGHT_FACTOR",
            "TF_EMA_WEIGHTS",
            "AI_ALIGN_WEIGHT",
            "ALIGN_BYPASS_ADX",
        ]:
            os.environ.pop(k, None)

    def test_lower_tf_dominance_scales_weights(self):
        indicators = {
            "M5": {
                "adx": FakeSeries([20, 40]),
                "ema_fast": FakeSeries([0.9, 1.1]),
                "ema_slow": FakeSeries([1.0, 1.0]),
            },
            "H1": {
                "ema_fast": FakeSeries([1.1, 1.0]),
                "ema_slow": FakeSeries([1.0, 1.0]),
            },
        }
        res = self.sf.is_multi_tf_aligned(indicators, ai_side=None)
        self.assertEqual(res, "long")


if __name__ == "__main__":
    unittest.main()
