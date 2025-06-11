from monitoring.safety_trigger import SafetyTrigger


def test_loss_limit_triggers():
    triggered = []
    st = SafetyTrigger(loss_limit=5)
    st.attach(lambda: triggered.append(True))
    st.record_loss(-6)
    assert triggered


def test_error_limit_triggers():
    triggered = []
    st = SafetyTrigger(error_limit=2)
    st.attach(lambda: triggered.append(True))
    st.record_error()
    assert not triggered
    st.record_error()
    assert triggered


def test_cooldown_prevents_retrigger():
    triggered = []
    st = SafetyTrigger(loss_limit=1, cooldown_sec=60)
    st.attach(lambda: triggered.append(True))
    st.record_loss(-1.5)
    assert triggered == [True]
    triggered.clear()
    st.record_loss(-1.5)
    assert triggered == []
