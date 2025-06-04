from backend.strategy.risk_manager import calc_lot_size
import pytest

def test_calc_lot_size():
    lot = calc_lot_size(10000, 0.01, 20, 0.1)
    assert round(lot, 2) == 50.0
    with pytest.raises(ValueError):
        calc_lot_size(10000, 0.01, 0, 0.1)
import unittest
import logging
from backend.risk_manager import (
    validate_rrr,
    validate_sl,
    calc_min_sl,
    get_recent_swing_diff,
    cost_guard,
)


class TestRiskManager(unittest.TestCase):
    def test_validate_rrr(self):
        self.assertTrue(validate_rrr(20, 10, 1.5))
        self.assertFalse(validate_rrr(10, 20, 2))

    def test_validate_sl_logs(self):
        logger = logging.getLogger('backend.risk_manager')
        with self.assertLogs(logger, level='WARNING') as cm:
            result = validate_sl(30, 5, 10, 1.0)
        self.assertFalse(result)
        self.assertTrue(any('SL too tight' in m for m in cm.output))
        self.assertTrue(validate_sl(30, 15, 10, 1.0))

    def test_calc_min_sl(self):
        self.assertEqual(calc_min_sl(10, 8, atr_mult=1.2, swing_buffer_pips=5), 13)

    def test_get_recent_swing_diff(self):
        candles = [
            {"mid": {"h": 1.1, "l": 1.0}},
            {"mid": {"h": 1.2, "l": 1.05}},
        ]
        diff = get_recent_swing_diff(candles, "long", 1.15, 0.01, lookback=2)
        self.assertAlmostEqual(diff, 15.0)

    def test_cost_guard(self):
        import os
        os.environ["MIN_NET_TP_PIPS"] = "2"
        self.assertTrue(cost_guard(5, 2))
        self.assertFalse(cost_guard(3, 2.5))
        os.environ.pop("MIN_NET_TP_PIPS", None)


if __name__ == '__main__':
    unittest.main()
