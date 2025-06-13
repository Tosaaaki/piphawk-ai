import importlib

from apscheduler.schedulers.base import STATE_RUNNING
from fastapi.testclient import TestClient

from backend.api import main


def test_panic_stop(monkeypatch):
    monkeypatch.setattr(main, "schedule_hourly_summary_job", lambda: None)
    monkeypatch.setattr(main.order_mgr, "close_all_positions", lambda: ["ok"])
    sent = []
    monkeypatch.setattr(main, "send_line_message", lambda msg: sent.append(msg))
    if main.scheduler.state != STATE_RUNNING:
        main.scheduler.start()
    client = TestClient(main.app)
    resp = client.post("/control/panic_stop")
    assert resp.status_code == 200
    assert main.scheduler.state != STATE_RUNNING
    assert sent and sent[0] == "Emergency Stop"
