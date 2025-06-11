import os
import sys
import types
import importlib
import unittest
import csv
import datetime
from datetime import timezone
from backend.utils import env_loader

class FakeSeries:
    def __init__(self, data):
        self._data = list(data)
        class _ILoc:
            def __init__(self, outer):
                self._outer = outer
            def __getitem__(self, idx):
                return self._outer._data[idx]
        self.iloc = _ILoc(self)
    def __getitem__(self, idx):
        return self._data[idx]
    def __len__(self):
        return len(self._data)

class TestRegimeFilters(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)

        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add("openai", openai_stub)
        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = "gpt"
        add("backend.utils.openai_client", oc)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "long"}, "risk": {}}
        oa.get_market_condition = lambda *a, **k: {"market_condition": "trend", "trend_direction": "long"}
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.calls = []
            def update_trade_sl(self, *a, **k):
                return {}
            def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False, with_oco=True):
                self.calls.append(side)
                return {"order_id": "1"}
            def cancel_order(self, oid):
                pass
            def place_market_order(self, *a, **k):
                pass
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        upd_mod = types.ModuleType("backend.logs.update_oanda_trades")
        def stop(*a, **k):
            raise SystemExit()
        upd_mod.update_oanda_trades = stop
        upd_mod.fetch_trade_details = lambda *a, **k: {}
        add("backend.logs.update_oanda_trades", upd_mod)

        stub_names = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.exit_logic",
            "backend.orders.position_manager",
            "backend.strategy.signal_filter",
            "backend.strategy.higher_tf_analysis",
            "backend.utils.notification",
            "backend.strategy.pattern_scanner",
            "backend.strategy.momentum_follow",
        ]
        for name in stub_names:
            mod = types.ModuleType(name)
            add(name, mod)

        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data", "range_sample.csv")
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            self._rows = list(reader)
        self._index = 0
        self._candles = []

        def fetch_multiple_timeframes(*a, **k):
            if self._index < len(self._rows):
                row = self._rows[self._index]
                candle = {
                    "time": row["time"],
                    "volume": int(row["volume"]),
                    "complete": True,
                    "mid": {"o": row["open"], "h": row["high"], "l": row["low"], "c": row["close"]},
                }
                self._candles.append(candle)
            return {"M5": list(self._candles), "M1": [], "H1": [], "H4": [], "D": []}

        def fetch_tick_data(*a, **k):
            price = float(self._candles[-1]["mid"]["c"]) if self._candles else 1.0
            return {"prices": [{"bids": [{"price": str(price)}], "asks": [{"price": str(price)}], "tradeable": True}]}

        def calc_ind(candles, *a, **k):
            vols = [int(c["volume"]) for c in candles]
            length = len(candles)
            return {
                "rsi": FakeSeries([50] * length),
                "atr": FakeSeries([0.1] * length),
                "ema_fast": FakeSeries([1.0] * length),
                "ema_slow": FakeSeries([1.0] * length),
                "bb_upper": FakeSeries([1.2] * length),
                "bb_lower": FakeSeries([0.8] * length),
                "bb_middle": FakeSeries([1.0] * length),
                "macd_hist": FakeSeries([0.0] * length),
                "volume": FakeSeries(vols),
            }

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = fetch_tick_data
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = fetch_multiple_timeframes
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = calc_ind
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators_multi = lambda data, *a, **k: {"M5": calc_ind(data.get("M5", []))}
        sys.modules["backend.strategy.exit_logic"].process_exit = lambda *a, **k: None
        sys.modules["backend.orders.position_manager"].check_current_position = lambda *a, **k: None

        def current_time_jst():
            row = self._rows[self._index]
            dt = datetime.datetime.fromisoformat(row["time"].replace("Z", "+00:00")) + datetime.timedelta(hours=9)
            return dt.hour + dt.minute / 60.0

        def pass_entry_filter(indicators, price=None, indicators_m1=None, indicators_m15=None, indicators_h1=None, context=None):
            ma = int(env_loader.get_env("VOL_MA_PERIOD", "3"))
            vols = indicators["volume"]
            avg = sum(vols[-ma:]) / min(ma, len(vols))
            if avg < float(env_loader.get_env("MIN_VOL_MA", "100")):
                return False
            start = float(env_loader.get_env("QUIET_START_HOUR_JST", "0"))
            end = float(env_loader.get_env("QUIET_END_HOUR_JST", "0"))
            now = current_time_jst()
            in_quiet = (start < end and start <= now < end) or (start > end and (now >= start or now < end)) or (start == end)
            return not in_quiet

        sys.modules["backend.strategy.signal_filter"].pass_entry_filter = pass_entry_filter
        sys.modules["backend.strategy.signal_filter"].pass_exit_filter = lambda *a, **k: True
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}
        sys.modules["backend.utils.notification"].send_line_message = lambda *a, **k: None
        sys.modules["backend.strategy.pattern_scanner"].scan = lambda *a, **k: {}
        sys.modules["backend.strategy.pattern_scanner"].PATTERN_DIRECTION = {}
        sys.modules["backend.strategy.momentum_follow"].follow_breakout = lambda *a, **k: True

        os.environ["PIP_SIZE"] = "0.01"
        os.environ["QUIET_START_HOUR_JST"] = "0.75"
        os.environ["QUIET_END_HOUR_JST"] = "3.25"
        os.environ["QUIET2_START_HOUR_JST"] = "0.75"
        os.environ["QUIET2_END_HOUR_JST"] = "3.25"
        os.environ["QUIET2_ENABLED"] = "true"
        os.environ["MIN_VOL_MA"] = "100"
        os.environ["VOL_MA_PERIOD"] = "3"

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        jr.instrument_is_tradeable = lambda instrument: True
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=0)
        self.runner._manage_pending_limits = lambda *a, **k: None
        import time
        self._orig_sleep = time.sleep
        time.sleep = lambda *_a, **_k: None

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)
        import time
        time.sleep = self._orig_sleep

    def test_no_entry_during_quiet_hours(self):
        for _ in range(len(self._rows)):
            with self.assertRaises(SystemExit):
                self.runner.run()
            self._index += 1
        self.assertEqual(self.jr.order_mgr.calls, [])

if __name__ == "__main__":
    unittest.main()
