import os
import sys
import types
import importlib
import unittest

class TestPatternDetection(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["PATTERN_TFS"] = "M1,M5"
        os.environ.setdefault("PATTERN_MIN_BARS", "4")
        os.environ.setdefault("PATTERN_TOLERANCE", "0.001")
        os.environ.setdefault("PATTERN_EXCLUDE_TFS", "")
        import importlib
        import backend.strategy.pattern_scanner as ps
        importlib.reload(ps)
        self._added = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._added.append(name)
        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)
        oa = types.ModuleType("backend.strategy.openai_analysis")
        self.captured = {}
        def dummy_get_trade_plan(market_data, indicators, candles_dict, **k):
            self.captured.update(k.get("detected_patterns") or {})
            return {"entry": {"side": "no"}}
        oa.get_trade_plan = dummy_get_trade_plan
        add("backend.strategy.openai_analysis", oa)
        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def enter_trade(self, *a, **k):
                return {"order_id": "1"}
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)
        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)
        oc = types.ModuleType("backend.utils.oanda_client")
        oc.get_pending_entry_order = lambda instrument: None
        add("backend.utils.oanda_client", oc)
        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)
        os.environ.pop("PATTERN_TFS", None)
        os.environ.pop("PATTERN_MIN_BARS", None)
        os.environ.pop("PATTERN_TOLERANCE", None)
        os.environ.pop("PATTERN_EXCLUDE_TFS", None)

    def test_detect_double_top_bottom(self):
        m1 = [
            {"o":1.2,"h":1.25,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.3,"l":1.1,"c":1.2},
            {"o":1.2,"h":1.24,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.35,"l":1.1,"c":1.3},
        ]
        m5 = [
            {"o":1.0,"h":1.4,"l":0.9,"c":1.3},
            {"o":1.3,"h":1.4,"l":1.2,"c":1.3},
            {"o":1.3,"h":1.2,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.4,"l":1.1,"c":1.3},
            {"o":1.3,"h":1.1,"l":0.8,"c":0.9},
        ]
        market_data = {"prices": [{"instrument": "USD_JPY", "bids": [{"price": "1"}], "asks": [{"price": "1"}]}]}
        self.el.process_entry({}, m5, market_data, candles_dict={"M1": m1, "M5": m5}, patterns=["double_bottom","double_top"], tf_align=None)
        self.assertEqual(self.captured, {"M1": "double_bottom", "M5": "double_top"})

if __name__ == "__main__":
    unittest.main()
