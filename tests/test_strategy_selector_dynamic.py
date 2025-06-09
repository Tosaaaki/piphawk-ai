import sys
import importlib

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
finally:
    if orig_pandas is not None:
        sys.modules["pandas"] = orig_pandas
    else:
        sys.modules.pop("pandas", None)
