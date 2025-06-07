import sys
import importlib

orig_pandas = sys.modules.get("pandas")
try:
    sys.modules.pop("pandas", None)
    import pandas as pd
    sys.modules["pandas"] = pd
    try:
        import mabwiser.mab as _mm
        importlib.reload(_mm)
    except Exception:
        pass
    if "strategies.selector" in sys.modules:
        importlib.reload(sys.modules["strategies.selector"])
    from strategies import ScalpStrategy, TrendStrategy, StrategySelector

    def test_selector_basic():
        strategies = {
            "scalp": ScalpStrategy(),
            "trend": TrendStrategy(),
        }
        selector = StrategySelector(strategies, alpha=0.1)
        context = {"feat": 1.0}

        first = selector.select(context)
        assert first in strategies.values()

        selector.update("scalp", context, 1.0)
        selector.update("trend", context, 0.0)
        second = selector.select(context)
        assert second.name == "scalp"

    def test_selector_offline_policy(monkeypatch):
        strategies = {
            "scalp": ScalpStrategy(),
            "trend": TrendStrategy(),
        }
        selector = StrategySelector(strategies, use_offline_policy=True)
        class Stub:
            def select(self, _ctx):
                return "trend"

        selector.offline_policy = Stub()
        choice = selector.select({"x": 1})
        assert choice.name == "trend"
finally:
    if orig_pandas is not None:
        sys.modules["pandas"] = orig_pandas
    else:
        sys.modules.pop("pandas", None)
