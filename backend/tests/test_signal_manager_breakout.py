import unittest
from signals.signal_manager import SignalManager


class DummyDet:
    def __init__(self):
        self.called = False
    def breakout_entry(self, price):
        self.called = True
        return {"side": "short", "type": "breakout"}


class TestSignalManagerBreakout(unittest.TestCase):
    def test_open_called(self):
        det = DummyDet()
        mgr = SignalManager(detector=det)
        mgr.handle_price({"close": 1.0, "high": 1.0, "low": 1.0})
        self.assertTrue(det.called)
        self.assertEqual(mgr.opened, [{"side": "short", "type": "breakout"}])


if __name__ == "__main__":
    unittest.main()
