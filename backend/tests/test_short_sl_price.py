import unittest
from backend import risk_manager


class TestShortSLPrice(unittest.TestCase):
    def test_calc_short_sl_price(self):
        price = risk_manager.calc_short_sl_price(1.20, 10, 0.01)
        self.assertAlmostEqual(price, 1.205)
        self.assertIsNone(risk_manager.calc_short_sl_price(None, 10, 0.01))


if __name__ == '__main__':
    unittest.main()
