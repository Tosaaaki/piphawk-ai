import importlib
import os
import unittest


class TestReentryManager(unittest.TestCase):
    def setUp(self):
        os.environ['PIP_SIZE'] = '0.01'
        rm_mod = importlib.import_module('backend.reentry_manager')
        importlib.reload(rm_mod)
        self.rm = rm_mod.ReentryManager(trigger_pips_over_break=1)

    def tearDown(self):
        os.environ.pop('PIP_SIZE', None)

    def test_long_reentry(self):
        self.rm.record_sl_hit(100.0, 'long')
        # threshold: spread(0.01)+1pip(0.01)=0.02
        self.assertFalse(self.rm.should_reenter(100.015, spread=0.01))
        self.assertTrue(self.rm.should_reenter(100.03, spread=0.01))

    def test_short_reentry(self):
        self.rm.record_sl_hit(200.0, 'short')
        self.assertFalse(self.rm.should_reenter(199.985, spread=0.01))
        self.assertTrue(self.rm.should_reenter(199.97, spread=0.01))

if __name__ == '__main__':
    unittest.main()
from datetime import datetime, timedelta, timezone

from backend.strategy.reentry_manager import ReentryManager


def test_reentry_cooldown():
    rm = ReentryManager(cooldown_sec=60)
    now = datetime.now(timezone.utc)
    rm.record_stop("long", now)
    assert not rm.can_enter("long", now + timedelta(seconds=30))
    assert rm.can_enter("long", now + timedelta(seconds=61))
