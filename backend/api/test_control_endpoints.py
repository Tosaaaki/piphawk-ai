import importlib

from apscheduler.schedulers.base import STATE_RUNNING
from fastapi.testclient import TestClient

# FastAPIアプリをインポート
from backend.api import main


def test_scheduler_control(monkeypatch):
    """/control エンドポイントの状態遷移を確認"""
    # ジョブ登録を無効化
    monkeypatch.setattr(main, "schedule_hourly_summary_job", lambda: None)
    main.scheduler.remove_all_jobs()

    client = TestClient(main.app)

    # スケジューラが停止状態なら開始
    if main.scheduler.state != STATE_RUNNING:
        main.scheduler.start()

    # stop
    resp = client.post("/control/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"
    assert main.scheduler.state != STATE_RUNNING

    # start
    resp = client.post("/control/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert main.scheduler.state == STATE_RUNNING

    # restart
    before = main.scheduler
    resp = client.post("/control/restart")
    after = main.scheduler
    assert resp.status_code == 200
    assert resp.json()["status"] == "restarted"
    assert after.state == STATE_RUNNING
    assert after is not before
