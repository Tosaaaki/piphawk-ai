from signals.adx_strategy import choose_strategy, entry_signal


def test_choose_strategy():
    assert choose_strategy(15) == "none"
    assert choose_strategy(25) == "scalp"
    assert choose_strategy(35) == "trend_follow"


def test_entry_signal_scalp():
    adx = 25
    closes_m1 = [1] * 20 + [2]
    closes_s10 = list(range(20)) + [50]
    side = entry_signal(adx, closes_m1, closes_s10)
    assert side == "long"


def test_entry_signal_trend():
    adx = 40
    closes_m1 = [1, 2, 3]
    closes_s10 = [1, 2, 3]
    side = entry_signal(adx, closes_m1, closes_s10)
    assert side == "long"
