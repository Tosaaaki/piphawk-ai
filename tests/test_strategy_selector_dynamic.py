import sys
import importlib
import logging

orig_pandas = sys.modules.get("pandas")
try:
    sys.modules.pop("pandas", None)
    import pandas as pd
    sys.modules["pandas"] = pd
    if "strategies.selector" in sys.modules:
        importlib.reload(sys.modules["strategies.selector"])
    from strategies import ScalpStrategy, TrendStrategy, StrategySelector

    def test_selector_dimension_change():
        strategies = {"scalp": ScalpStrategy(), "trend": TrendStrategy()}
        selector = StrategySelector(strategies)
        ctx1 = {"a": 1.0}
        # initial select to trigger fit
        selector.select(ctx1)
        ctx2 = {"a": 1.0, "b": 2.0}
        # should not raise even though dimension differs
        result = selector.select(ctx2)
        assert result in strategies.values()

    def test_predict_retry(monkeypatch, caplog):
        strategies = {"scalp": ScalpStrategy(), "trend": TrendStrategy()}
        selector = StrategySelector(strategies)
        ctx = {"a": 1.0}

        call = {"n": 0}

        def flaky_predict(_):
            if call["n"] == 0:
                call["n"] += 1
                raise ValueError("boom")
            return "scalp"

        monkeypatch.setattr(selector.bandit, "predict", flaky_predict)

        ensure_count = {"n": 0}

        orig_ensure = selector._ensure_bandit_ready

        def count_ensure(c):
            ensure_count["n"] += 1
            orig_ensure(c)

        monkeypatch.setattr(selector, "_ensure_bandit_ready", count_ensure)

        caplog.set_level(logging.WARNING)
        result = selector.select(ctx)
        assert result.name == "scalp"
        assert call["n"] == 1
        assert ensure_count["n"] == 2
        assert any("num_features" in r.getMessage() for r in caplog.records)
finally:
    if orig_pandas is not None:
        sys.modules["pandas"] = orig_pandas
    else:
        sys.modules.pop("pandas", None)
