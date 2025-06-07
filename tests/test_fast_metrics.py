import unittest
from core.ring_buffer import RingBuffer
from fast_metrics import calc_mid_spread


class TestFastMetrics(unittest.TestCase):
    def test_calc_mid_spread(self):
        rb = RingBuffer(5)
        rb.append({"bid": 100, "ask": 100.02})
        rb.append({"bid": 100.01, "ask": 100.03})
        mid, spread = calc_mid_spread(rb, window=2)
        self.assertAlmostEqual(mid, 100.015)
        self.assertAlmostEqual(spread, 0.02)


if __name__ == "__main__":
    unittest.main()
