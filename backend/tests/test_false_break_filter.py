from backend.strategy.false_break_filter import is_false_breakout


def test_is_false_breakout_true():
    candles = []
    # build range data
    for i in range(22):
        candles.append({"mid": {"h": 1.1, "l": 1.0, "c": 1.05}, "complete": True})
    # breakout candle
    candles.append({"mid": {"h": 1.2, "l": 1.1, "c": 1.21}, "complete": True})
    # close back inside range
    candles.append({"mid": {"h": 1.18, "l": 1.08, "c": 1.09}, "complete": True})
    assert is_false_breakout(candles)


def test_is_false_breakout_false():
    candles = [{"mid": {"h": 1.1, "l": 1.0, "c": 1.05}, "complete": True}] * 25
    assert not is_false_breakout(candles)
