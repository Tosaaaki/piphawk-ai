import importlib
import unittest

import backend.strategy.openai_micro_scalp as micro
from backend.market_data.tick_metrics import calc_of_imbalance


class TestMicroScalp(unittest.TestCase):
    def test_of_imbalance_calc(self):
        ticks = [
            {"bid": 1.0, "ask": 1.01},
            {"bid": 1.01, "ask": 1.02},  # up
            {"bid": 1.0, "ask": 1.01},   # down
            {"bid": 1.02, "ask": 1.03},  # up
        ]
        val = calc_of_imbalance(ticks)
        self.assertAlmostEqual(val, (2 - 1) / 3)

    def test_load_prompt(self):
        text = micro.load_prompt()
        self.assertIn("breakout continuation", text.lower())

    def test_get_plan_json(self):
        micro.ask_openai = lambda *a, **k: '{"enter":true,"side":"long","tp_pips":1,"sl_pips":0.5}'
        plan = micro.get_plan({"of_imbalance": 0, "vol_burst": 0, "spd_avg": 0})
        self.assertTrue(plan["enter"])
        self.assertEqual(plan["side"], "long")
        self.assertAlmostEqual(plan["tp_pips"], 1.0)
        self.assertAlmostEqual(plan["sl_pips"], 0.5)


if __name__ == "__main__":
    unittest.main()
