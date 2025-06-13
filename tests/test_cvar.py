import pytest

from risk.cvar import calc_cvar


def test_calc_cvar_basic():
    returns = [1.0, -2.0, -1.0, 3.0, -4.0]
    result = calc_cvar(returns, alpha=0.4)
    assert result == pytest.approx((-4.0 - 2.0)/2)


def test_calc_cvar_rounding():
    returns = [1.0, -2.0, -1.0, 3.0, -4.0]
    result = calc_cvar(returns, alpha=0.3)
    assert result == pytest.approx((-4.0 - 2.0) / 2)


def test_calc_cvar_errors():
    with pytest.raises(ValueError):
        calc_cvar([])
    with pytest.raises(ValueError):
        calc_cvar([1,2], alpha=0)

