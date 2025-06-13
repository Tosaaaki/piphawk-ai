import unittest

from backend.indicators.pivot import calculate_pivots


class TestPivotCalc(unittest.TestCase):
    def test_levels(self):
        res = calculate_pivots(2.0, 1.0, 1.5)
        self.assertAlmostEqual(res["pivot"], 1.5)
        self.assertAlmostEqual(res["r1"], 2.0)
        self.assertAlmostEqual(res["s1"], 1.0)
        self.assertAlmostEqual(res["r2"], 2.5)
        self.assertAlmostEqual(res["s2"], 0.5)


if __name__ == "__main__":
    unittest.main()
