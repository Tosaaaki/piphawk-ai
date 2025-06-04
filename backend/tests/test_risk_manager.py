from backend.strategy.risk_manager import calc_lot_size
import pytest

def test_calc_lot_size():
    lot = calc_lot_size(10000, 0.01, 20, 0.1)
    assert round(lot, 2) == 50.0
    with pytest.raises(ValueError):
        calc_lot_size(10000, 0.01, 0, 0.1)
