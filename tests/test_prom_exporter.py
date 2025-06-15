from fastapi.testclient import TestClient

from monitoring import prom_exporter as pe


def test_metrics_endpoint():
    client = TestClient(pe.app)
    pe.increment_trade_mode("scalp")
    pe.record_ai_confidence(0.5)
    pe.increment_rl_override()
    pe.increment_pattern_filter_pass()
    pe.record_position_age(120)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "trade_mode_count_total" in body
    assert "ai_confidence_bucket" in body
    assert "rl_override_total" in body
    assert "pattern_filter_pass_total" in body
    assert "position_max_age_seconds" in body
