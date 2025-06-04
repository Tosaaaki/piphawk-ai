from backend.strategy.risk_manager import calc_lot_size
import pytest

def test_calc_lot_size():
    lot = calc_lot_size(10000, 0.01, 20, 0.1)
    assert round(lot, 2) == 50.0
    with pytest.raises(ValueError):
        calc_lot_size(10000, 0.01, 0, 0.1)
import unittest
import logging
from backend.risk_manager import validate_rrr, validate_sl


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


if __name__ == '__main__':
    unittest.main()
