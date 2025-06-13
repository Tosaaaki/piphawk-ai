import unittest

import signals.signal_manager as sm


class TestSignalManager(unittest.TestCase):
    def test_detect_range_reversal_true(self):
        candles = [
            {"o": 1.0, "c": 0.95, "h": 1.05, "l": 0.94},
            {"o": 0.9, "c": 1.05, "h": 1.06, "l": 0.89},
        ]
        mode = sm.detect_range_reversal(
            vwap_dev=2.0,
            atr_boost=1.0,
            candles=candles,
            confluence=False,
        )
        self.assertEqual(mode, "range_reversal")

    def test_detect_range_reversal_none(self):
        candles = [
            {"o": 1.0, "c": 1.05, "h": 1.06, "l": 0.99},
            {"o": 1.06, "c": 1.07, "h": 1.08, "l": 1.05},
        ]
        mode = sm.detect_range_reversal(
            vwap_dev=0.5,
            atr_boost=0.2,
            candles=candles,
            confluence=False,
        )
        self.assertIsNone(mode)


if __name__ == "__main__":
    unittest.main()
