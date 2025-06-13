import unittest

import pandas as pd

from selector_fast import RuleSelector, build_entry_context
from strategies.scalp import entry_rules


class TestRuleSelector(unittest.TestCase):
    def test_basic_selection(self):
        rules = {
            "long": entry_rules.rule_scalp_long,
            "short": entry_rules.rule_scalp_short,
            "breakout": entry_rules.rule_breakout,
        }
        selector = RuleSelector(rules, alpha=0.1)
        ctx_raw = {
            "mid": 1.0,
            "spread": 0.01,
            "lower_band": 1.0,
            "upper_band": 1.1,
            "range_high": 1.2,
            "range_low": 0.9,
            "price": 1.21,
            "adx": 25,
        }
        ctx = build_entry_context(ctx_raw)
        selector.update_reward("long", ctx, 1.0)
        selector.update_reward("short", ctx, 0.0)
        side = selector.evaluate(ctx_raw)
        self.assertEqual(side, "long")

    def test_context_builder(self):
        data = {
            "spread": 0.02,
            "mid": 1.1,
            "upper_band": 1.3,
            "lower_band": 1.0,
            "price": 1.2,
            "range_high": 1.25,
            "range_low": 1.0,
            "adx": 30,
        }
        ctx = build_entry_context(data)
        self.assertAlmostEqual(ctx["spread"], 0.02)
        self.assertAlmostEqual(ctx["dist_upper"], 0.2)
        self.assertAlmostEqual(ctx["dist_lower"], 0.1)
        self.assertAlmostEqual(ctx["dist_high"], 0.05)
        self.assertAlmostEqual(ctx["dist_low"], 0.2)
        self.assertAlmostEqual(ctx["adx"], 30)


if __name__ == "__main__":
    unittest.main()
