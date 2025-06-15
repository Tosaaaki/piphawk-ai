import types
from datetime import datetime, timedelta, timezone

import vcr

from execution import position_manager as pm
from execution.position_manager import update_trailing_sl
from piphawk_ai.tech_arch.market_context import MarketContext
from piphawk_ai.vote_arch.ai_entry_plan import EntryPlan

my_vcr = vcr.VCR(cassette_library_dir='tests/cassettes')


class DummyOM:
    def __init__(self):
        self.calls: list[tuple[float, float]] = []

    def place_market_with_tp_sl(self, instrument, units, side, tp_pips, sl_pips, comment_json=None):
        self.calls.append((tp_pips, sl_pips))
        return {"orderFillTransaction": {"id": "1", "tradeOpened": {"tradeID": "t"}}}


class FakeSeries:
    def __init__(self, val):
        class _IL:
            def __getitem__(self, idx):
                return val

        self.iloc = _IL()
        self._val = val

    def __getitem__(self, idx):
        return self._val


def test_create_split_orders(monkeypatch):
    dummy = DummyOM()
    monkeypatch.setattr(pm, "OrderManager", lambda: dummy)
    monkeypatch.setattr(pm, "calculate_atr", lambda *a, **k: FakeSeries(0.01))
    plan = EntryPlan(side="long", tp=1.0, sl=0.5, lot=1.0)
    orders = pm.create_split_orders("trend_follow", plan)
    assert len(orders) == 2
    assert dummy.calls[0] == (1.0, 0.5)
    assert dummy.calls[1] == (0.016, 0.007)


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


