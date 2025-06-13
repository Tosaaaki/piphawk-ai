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


class TestTfWeightNormalization(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["TF_EMA_WEIGHTS"] = "M5:0.1,M15:0.1,H1:0.1"
        os.environ["AI_ALIGN_WEIGHT"] = "0"
        os.environ["ALIGN_BYPASS_ADX"] = "0"
        import analysis.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf

    def tearDown(self):
        for k in ["TF_EMA_WEIGHTS", "AI_ALIGN_WEIGHT", "ALIGN_BYPASS_ADX"]:
            os.environ.pop(k, None)

    def test_normalization_changes_result(self):
        indicators = {
            "M5": {"ema_fast": FakeSeries([1, 1.1]), "ema_slow": FakeSeries([1, 1])},
            "M15": {"ema_fast": FakeSeries([1, 1.1]), "ema_slow": FakeSeries([1, 1])},
            "H1": {"ema_fast": FakeSeries([1, 1.1]), "ema_slow": FakeSeries([1, 1])},
        }
        self.assertEqual(self.sf.is_multi_tf_aligned(indicators), "long")


if __name__ == "__main__":
    unittest.main()
