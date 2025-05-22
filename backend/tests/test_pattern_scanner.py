import unittest
from backend.strategy.pattern_scanner import scan

class TestPatternScanner(unittest.TestCase):
    def test_scan_returns_dict(self):
        candles = {"M5": [{"o":1,"h":2,"l":0.5,"c":1.5}]}
        result = scan(candles, ["double_bottom"], mode="local")
        self.assertIn("M5", result)

if __name__ == "__main__":
    unittest.main()
