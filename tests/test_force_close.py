import os

import pandas as pd

from backend.orders import order_manager

os.environ.setdefault('OANDA_API_KEY', 'x')
os.environ.setdefault('OANDA_ACCOUNT_ID', 'x')
os.environ.setdefault('OPENAI_API_KEY', 'x')
import sys
from types import ModuleType


class Dummy:
    def __init__(self, *a, **k):
        pass
sys.modules.setdefault('linebot', ModuleType('linebot'))
kline = sys.modules['linebot']
kline.LineBotApi = Dummy
kline.models = ModuleType('models')
kline.models.TextSendMessage = Dummy
sys.modules['linebot.models'] = kline.models
kafka_mod = ModuleType('kafka')
kafka_mod.KafkaProducer = Dummy
sys.modules.setdefault('kafka', kafka_mod)
prom_mod = ModuleType('prometheus_client')
prom_mod.Gauge = Dummy
sys.modules.setdefault('prometheus_client', prom_mod)
from backend.scheduler.job_runner import JobRunner
from piphawk_ai.risk.manager import PortfolioRiskManager


def test_close_all_positions(monkeypatch):
    calls = []
    monkeypatch.setattr('backend.orders.position_manager.get_open_positions', lambda: [{'instrument': 'USD_JPY'}, {'instrument': 'EUR_USD'}])
    def fake_close(self, instrument, side='both'):
        calls.append(instrument)
        return {'ok': True}
    monkeypatch.setattr(order_manager.OrderManager, 'close_position', fake_close)
    om = order_manager.OrderManager()
    res = om.close_all_positions()
    assert calls == ['USD_JPY', 'EUR_USD']
    assert len(res) == 2


def test_update_portfolio_risk_triggers_close(monkeypatch):
    jr = JobRunner(interval_seconds=0)
    jr.risk_mgr = PortfolioRiskManager(max_cvar=1.0, alpha=0.5)
    monkeypatch.setattr(jr, '_get_recent_trade_pl', lambda limit=50: [-2.0])
    monkeypatch.setattr('backend.orders.position_manager.get_open_positions', lambda: [])
    closed = []
    import backend.scheduler.job_runner as jr_mod
    monkeypatch.setattr(jr_mod.order_mgr, 'close_all_positions', lambda: closed.append(True))
    monkeypatch.setenv('FORCE_CLOSE_ON_RISK', 'true')
    jr._update_portfolio_risk()
    assert closed
