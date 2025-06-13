import logging
import pickle

from strategies import ScalpStrategy, StrategySelector, TrendStrategy


class DummyPolicy:
    def select(self, _ctx):
        return "trend"


def test_strategy_selector_offline(tmp_path, monkeypatch, caplog):

    policy_file = tmp_path / "policy.pkl"
    with open(policy_file, "wb") as f:
        pickle.dump(DummyPolicy(), f)

    monkeypatch.setenv("USE_OFFLINE_POLICY", "true")
    monkeypatch.setenv("POLICY_PATH", str(policy_file))

    strategies = {"scalp": ScalpStrategy(), "trend": TrendStrategy()}
    caplog.set_level(logging.INFO)
    selector = StrategySelector(strategies)
    result = selector.select({"x": 1})
    assert result.name == "trend"
    assert any("OfflinePolicy selected: trend" in r.message for r in caplog.records)

