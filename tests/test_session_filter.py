from filters import session_filter


def test_apply_filters_market_closed(monkeypatch):
    monkeypatch.setattr(session_filter, "_in_trade_hours", lambda: False)
    ok, ctx, reason = session_filter.apply_filters(0.1, 0.2, None, tradeable=True)
    assert not ok
    assert reason == "market_closed"


def test_apply_filters_quiet_hours(monkeypatch):
    monkeypatch.setattr(session_filter, "is_quiet_hours", lambda *a, **k: True)
    ok, ctx, reason = session_filter.apply_filters(0.1, 0.2, None, tradeable=True)
    assert not ok
    assert reason == "session"


def test_apply_filters_wide_spread(monkeypatch):
    monkeypatch.setattr(session_filter, "_in_trade_hours", lambda: True)
    monkeypatch.setattr(session_filter, "is_quiet_hours", lambda *a, **k: False)
    monkeypatch.setenv("MAX_SPREAD_PIPS", "1")
    ok, ctx, reason = session_filter.apply_filters(0.1, 0.2, 2.0, tradeable=True)
    assert not ok
    assert reason == "wide_spread"


def test_is_quiet_hours_jst_false():
    from datetime import datetime, timezone

    dt = datetime(2023, 1, 1, 4, 0, tzinfo=timezone.utc)
    assert not session_filter.is_quiet_hours(dt)


def test_is_quiet_hours_jst_true():
    from datetime import datetime, timezone

    dt = datetime(2023, 1, 1, 20, 0, tzinfo=timezone.utc)
    assert session_filter.is_quiet_hours(dt)
