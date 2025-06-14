import os
from datetime import datetime, timedelta, timezone

import vcr

from execution.position_manager import create_split_orders, update_trailing_sl
from piphawk_ai.tech_arch.market_context import MarketContext
from piphawk_ai.vote_arch.ai_entry_plan import EntryPlan

my_vcr = vcr.VCR(cassette_library_dir='tests/cassettes')


@my_vcr.use_cassette('split_orders.yaml', record_mode='none')
def test_create_split_orders(monkeypatch):
    monkeypatch.setenv('OANDA_ACCOUNT_ID', 'acc')
    monkeypatch.setenv('OANDA_API_KEY', 'k')
    monkeypatch.setenv('OANDA_API_URL', 'http://localhost:9999')
    plan = EntryPlan(side='long', tp=1.0, sl=0.5, lot=1.0)
    orders = create_split_orders('trend_follow', plan)
    assert len(orders) == 2


@my_vcr.use_cassette('split_orders.yaml', record_mode='none')
def test_update_trailing_sl(monkeypatch):
    monkeypatch.setenv('OANDA_ACCOUNT_ID', 'acc')
    monkeypatch.setenv('OANDA_API_KEY', 'k')
    monkeypatch.setenv('OANDA_API_URL', 'http://localhost:9999')
    now = datetime.now(timezone.utc)
    candles = []
    for i in range(20):
        t = (now - timedelta(minutes=5 * (19 - i))).isoformat()
        candles.append({'time': t, 'mid': {'h': '1.2', 'l': '1.0', 'c': '1.1'}})
    ctx = MarketContext(candles=candles, tick=None, spread=0.0)
    update_trailing_sl('t1', ctx)
