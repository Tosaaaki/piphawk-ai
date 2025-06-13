import unittest

from backend.utils.price import format_price


class TestPriceFormat(unittest.TestCase):
    def test_jpy_pair_rounding(self):
        self.assertEqual(format_price("USD_JPY", 143.2509), "143.251")

    def test_non_jpy_pair_rounding(self):
        self.assertEqual(format_price("EUR_USD", 1.234567), "1.23457")

if __name__ == "__main__":
    unittest.main()
