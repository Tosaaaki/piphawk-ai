import pytest

from signals.composite_filter import CompositeFilter, bb_break, rsi_edge

CASES = [
    ({"rsi": 25, "price": 102, "bb_upper": 101, "bb_lower": 99}, True),
    ({"rsi": 25, "price": 100, "bb_upper": 101, "bb_lower": 99}, False),
    ({"rsi": 50, "price": 102, "bb_upper": 101, "bb_lower": 99}, False),
    ({"rsi": 25, "price": 102, "bb_upper": 101, "bb_lower": 99}, True),
    ({"rsi": 25, "price": 100, "bb_upper": 101, "bb_lower": 99}, False),
    ({"rsi": 50, "price": 102, "bb_upper": 101, "bb_lower": 99}, False),
    ({"rsi": 50, "price": 100, "bb_upper": 101, "bb_lower": 99}, False),
    ({"rsi": 80, "price": 102, "bb_upper": 101, "bb_lower": 99}, True),
    ({"rsi": 80, "price": 100, "bb_upper": 101, "bb_lower": 99}, False),
    ({"rsi": 50, "price": 100, "bb_upper": 101, "bb_lower": 99}, False),
]


@pytest.mark.parametrize("ctx, expected", CASES)
def test_composite_filter(ctx, expected):
    flt = CompositeFilter(min_score=2, weights={"rsi_edge": 1, "bb_break": 1})
    flt.register("rsi_edge", rsi_edge)
    flt.register("bb_break", bb_break)
    assert flt.pass_(ctx) is expected
