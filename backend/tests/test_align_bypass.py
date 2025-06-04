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


class TestAlignBypass(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["ALIGN_BYPASS_ADX"] = "25"
        import analysis.signal_filter as sf
        importlib.reload(sf)
        self.sf = sf
        self.logger = sf.logger

    def tearDown(self):
        os.environ.pop("ALIGN_BYPASS_ADX", None)

    def test_high_adx_bypasses_alignment(self):
        indicators = {
            "M5": {
                "adx": FakeSeries([20, 30]),
                "ema_fast": FakeSeries([1.0, 0.9]),
                "ema_slow": FakeSeries([1.0, 1.1]),
            },
            "H1": {
                "ema_fast": FakeSeries([1.0, 0.9]),
                "ema_slow": FakeSeries([1.0, 1.1]),
            },
        }
        with self.assertLogs(self.logger, level="DEBUG") as cm:
            res = self.sf.is_multi_tf_aligned(indicators, ai_side="long")
        self.assertEqual(res, "long")
        self.assertTrue(any("bypass" in m.lower() for m in cm.output))


if __name__ == "__main__":
    unittest.main()
