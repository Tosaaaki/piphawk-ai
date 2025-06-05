import unittest

import backend.indicators.vwap_band as vb


class TestVWAPBand(unittest.TestCase):
    def setUp(self):
        vb.deviation_history.clear()

    def test_basic_delta(self):
        prices = [100, 101, 102]
        volumes = [1, 1, 1]
        d, r = vb.get_vwap_delta(prices, volumes)
        self.assertAlmostEqual(d, 1.0)
        self.assertAlmostEqual(r, 1.0)

    def test_history_ratio(self):
        vb.get_vwap_delta([1, 1, 1], [1, 1, 1])  # deviation 0
        d, r = vb.get_vwap_delta([1, 2, 1], [1, 1, 1])
        self.assertNotEqual(r, 0.0)
        self.assertAlmostEqual(d, 1 - (4/3), places=5)


if __name__ == "__main__":
    unittest.main()
