import pytest
from piphawk_ai.analysis import calculate_trade_score


@pytest.mark.parametrize(
    "time_str, side",
    [
        ("08:25", "long"),
        ("09:40", "short"),
    ],
)
def test_trade_score_threshold(time_str: str, side: str) -> None:
    score = calculate_trade_score(time_str, side)
    assert score >= 0.6

