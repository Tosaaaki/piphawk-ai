import pytest

from signals.composite_filter import CompositeFilter, ai_pattern, bb_break, rsi_edge

CASES = [
    ({"rsi": 25, "price": 102, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 0}, True),
    ({"rsi": 25, "price": 100, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 1}, True),
    ({"rsi": 50, "price": 102, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 1}, True),
    ({"rsi": 25, "price": 102, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 1}, True),
    ({"rsi": 25, "price": 100, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 0}, False),
    ({"rsi": 50, "price": 102, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 0}, False),
    ({"rsi": 50, "price": 100, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 1}, False),
    ({"rsi": 80, "price": 102, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 0}, True),
    ({"rsi": 80, "price": 100, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 0}, False),
    ({"rsi": 50, "price": 100, "bb_upper": 101, "bb_lower": 99, "ai_pattern": 0}, False),
]


@pytest.mark.parametrize("ctx, expected", CASES)
def test_composite_filter(ctx, expected):
    flt = CompositeFilter(min_score=2, weights={"rsi_edge": 1, "bb_break": 1, "ai_pattern": 1})
    flt.register("rsi_edge", rsi_edge)
    flt.register("bb_break", bb_break)
    flt.register("ai_pattern", ai_pattern)
    assert flt.pass_(ctx) is expected
