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

class TestPullbackPrompt(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        pandas_stub = importlib.import_module("types").ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        import sys
        sys.modules["pandas"] = pandas_stub
        import backend.strategy.openai_prompt as op
        importlib.reload(op)
        self.op = op

    def test_prompt_contains_pullback_status(self):
        ind_dummy = {
            "rsi": FakeSeries([50]*20),
            "atr": FakeSeries([0]*20),
            "adx": FakeSeries([20]*20),
            "bb_upper": FakeSeries([1]*20),
            "bb_lower": FakeSeries([0]*20),
            "ema_fast": FakeSeries([1]*20),
            "ema_slow": FakeSeries([1]*20),
        }
        candles_dummy = [{"mid": {"h": 1, "l": 0}}]*60
        prompt, _ = self.op.build_trade_plan_prompt(
            ind_dummy,
            ind_dummy,
            ind_dummy,
            ind_dummy,
            candles_dummy,
            candles_dummy,
            candles_dummy,
            candles_dummy,
            {},
            None,
            True,
        )
        self.assertIn("Pullback Completed", prompt)
        self.assertIn("True", prompt)

if __name__ == "__main__":
    unittest.main()
