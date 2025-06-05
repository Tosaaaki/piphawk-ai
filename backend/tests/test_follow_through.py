import importlib
import unittest


def _c(c):
    return {"o": "0", "h": "0", "l": "0", "c": str(c)}


class TestFollowThrough(unittest.TestCase):
    def setUp(self):
        import signals.signal_manager as sm
        importlib.reload(sm)
        self.sm = sm

    def test_follow_through(self):
        self.assertTrue(self.sm.follow_through_ok(_c(1.0), _c(1.1), "long"))
        self.assertFalse(self.sm.follow_through_ok(_c(1.0), _c(0.9), "long"))
        self.assertTrue(self.sm.follow_through_ok(_c(1.0), _c(0.9), "short"))


if __name__ == '__main__':
    unittest.main()
