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

def _ind():
    return {
        "rsi": FakeSeries([50]*20),
        "atr": FakeSeries([0]*20),
        "adx": FakeSeries([20]*20),
        "bb_upper": FakeSeries([1]*20),
        "bb_lower": FakeSeries([0]*20),
        "ema_fast": FakeSeries([1]*20),
        "ema_slow": FakeSeries([1]*20),
    }

class TestCandleSummary(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        pandas_stub = importlib.import_module("types").ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        import sys
        sys.modules["pandas"] = pandas_stub
        import backend.strategy.openai_prompt as op
        importlib.reload(op)
        self.op = op

    def test_summary_included(self):
        ind = _ind()
        candles = [{"mid": {"o": 1, "h": 1, "l": 0, "c": 1}}]*20
        prompt, _ = self.op.build_trade_plan_prompt(
            ind, ind, ind, ind,
            candles, candles, candles, candles,
            {}, None,
            False,
            summarize_candles=True,
        )
        self.assertIn('"open_avg":1.0', prompt)

    def test_summary_disabled_by_default(self):
        ind = _ind()
        candles = [{"mid": {"o": 1, "h": 1, "l": 0, "c": 1}}]*20
        prompt, _ = self.op.build_trade_plan_prompt(
            ind, ind, ind, ind,
            candles, candles, candles, candles,
            {}, None,
            False,
        )
        self.assertNotIn('"open_avg":1.0', prompt)

if __name__ == "__main__":
    unittest.main()
