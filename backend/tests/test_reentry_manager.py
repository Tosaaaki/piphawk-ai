from datetime import datetime, timedelta
from backend.strategy.reentry_manager import ReentryManager


def test_reentry_cooldown():
    rm = ReentryManager(cooldown_sec=60)
    now = datetime.utcnow()
    rm.record_stop("long", now)
    assert not rm.can_enter("long", now + timedelta(seconds=30))
    assert rm.can_enter("long", now + timedelta(seconds=61))
