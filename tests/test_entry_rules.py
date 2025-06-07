import unittest
from strategies.scalp import entry_rules


class TestEntryRules(unittest.TestCase):
    def test_rules(self):
        ctx = {"mid": 1.0, "spread": 0.01, "lower_band": 1.0, "upper_band": 1.1, "range_high": 1.2, "range_low": 0.9, "price": 1.21}
        self.assertEqual(entry_rules.rule_scalp_long(ctx), "long")
        self.assertEqual(entry_rules.rule_scalp_short(ctx), None)
        self.assertEqual(entry_rules.rule_breakout(ctx), "long")


if __name__ == "__main__":
    unittest.main()
