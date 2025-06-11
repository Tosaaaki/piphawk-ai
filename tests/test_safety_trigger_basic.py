from monitoring.safety_trigger import SafetyTrigger


def test_safety_trigger_loss(monkeypatch):
    called = []
    st = SafetyTrigger(loss_limit=1.0)
    st.attach(lambda: called.append(True))
    st.record_loss(-1.5)
    assert called == [True]


def test_safety_trigger_error(monkeypatch):
    called = []
    st = SafetyTrigger(error_limit=2)
    st.attach(lambda: called.append(True))
    st.record_error()
    assert not called
    st.record_error()
    assert called == [True]
