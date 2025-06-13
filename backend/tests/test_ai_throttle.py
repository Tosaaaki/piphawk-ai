import importlib

import backend.core.ai_throttle as throttle


def test_get_cooldown_defaults(monkeypatch):
    monkeypatch.delenv("SCALP_MOMENTUM_COOLDOWN_SEC", raising=False)
    monkeypatch.delenv("AI_COOLDOWN_SEC", raising=False)
    assert throttle.get_cooldown("scalp_momentum") == 20
    assert throttle.get_cooldown("trend_follow") == 60


def test_get_cooldown_env_override(monkeypatch):
    monkeypatch.setenv("SCALP_MOMENTUM_COOLDOWN_SEC", "15")
    monkeypatch.setenv("AI_COOLDOWN_SEC", "90")
    importlib.reload(throttle)
    assert throttle.get_cooldown("scalp_momentum") == 15
    assert throttle.get_cooldown("scalp") == 90
