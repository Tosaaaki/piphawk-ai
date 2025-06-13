import pytest

from backend.strategy.risk_manager import calc_lot_size
from piphawk_ai.risk.manager import PortfolioRiskManager


def test_portfolio_risk_manager_basic():
    mgr = PortfolioRiskManager(max_cvar=2.0, alpha=0.5)
    mgr.update_risk_metrics([-1.0, -3.0], [])
    assert mgr.check_stop_conditions()
    lot = calc_lot_size(10000, 0.01, 20, 0.1, risk_engine=mgr)
    assert lot == 0.0


def test_portfolio_risk_manager_reduction():
    mgr = PortfolioRiskManager(max_cvar=5.0, alpha=0.5)
    mgr.update_risk_metrics([-1.0, -3.0], [])
    lot = calc_lot_size(10000, 0.01, 20, 0.1, risk_engine=mgr)
    base = calc_lot_size(10000, 0.01, 20, 0.1)
    assert 0 < lot < base


def test_allowed_lot_default_env(monkeypatch):
    monkeypatch.setenv("RISK_PER_TRADE", "0.02")
    mgr = PortfolioRiskManager(max_cvar=10.0)
    lot = mgr.get_allowed_lot(10000, sl_pips=25, pip_value=0.1)
    assert lot == pytest.approx(80.0)
