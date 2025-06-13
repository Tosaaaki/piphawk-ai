import pytest

from backend.utils.price import format_price


def test_jpy_pair_rounding():
    assert format_price("USD_JPY", 143.2509) == "143.251"


def test_non_jpy_pair_rounding():
    assert format_price("EUR_USD", 1.234567) == "1.23457"
