import unittest

from piphawk_ai.analysis.regime_detector import RegimeDetector


class DummyTick(dict):
    def __getattr__(self, item):
        return self[item]


def make_tick(price: float) -> DummyTick:
    return DummyTick(high=price + 0.05, low=price - 0.05, close=price)


class TestRegimeDetector(unittest.TestCase):
    def test_transition_to_trend(self):
        rd = RegimeDetector(
            len_fast=3,
            bw_mult=0.5,
            atr_mult=0.5,
            adx_threshold=1,
            adx_slope=0,
            bb_window=3,
            keltner_window=3,
        )
        # 初期レンジ
        for p in [1.0, 1.01, 1.02, 1.01]:
            rd.update(make_tick(p))
        res = rd.update(DummyTick(high=1.3, low=1.0, close=1.28))
        self.assertTrue(res["transition"])
        self.assertEqual(rd.state, "TREND")


if __name__ == "__main__":
    unittest.main()
