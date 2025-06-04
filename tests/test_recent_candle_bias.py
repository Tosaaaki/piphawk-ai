import os
import sys
import types
import importlib
import unittest


class TestRecentCandleBias(unittest.TestCase):
    def setUp(self):
        self._added = []

        def add(name: str, mod: types.ModuleType):
            sys.modules[name] = mod
            self._added.append(name)

        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = "gpt"
        add("backend.utils.openai_client", oc)

        dp = types.ModuleType("backend.strategy.dynamic_pullback")
        dp.calculate_dynamic_pullback = lambda *a, **k: 0.0
        add("backend.strategy.dynamic_pullback", dp)

        adx_mod = types.ModuleType("backend.indicators.adx")
        adx_mod.calculate_adx_slope = lambda *a, **k: 0.0
        add("backend.indicators.adx", adx_mod)

        exit_mod = types.ModuleType("backend.strategy.exit_ai_decision")
        exit_mod.AIDecision = type("AIDecision", (), {})
        exit_mod.evaluate = lambda *a, **k: None
        add("backend.strategy.exit_ai_decision", exit_mod)

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)
        os.environ.pop("REV_BLOCK_BARS", None)
        os.environ.pop("TAIL_RATIO_BLOCK", None)
        os.environ.pop("VOL_SPIKE_PERIOD", None)
        sys.modules.pop("backend.strategy.openai_analysis", None)

    def test_blocks_opposite_tail(self):
        os.environ["REV_BLOCK_BARS"] = "1"
        os.environ["TAIL_RATIO_BLOCK"] = "2.0"
        os.environ["VOL_SPIKE_PERIOD"] = "1"
        candles = [
            {"o": 1.0, "h": 1.0, "l": 1.0, "c": 1.0, "volume": 100},
            {"o": 1.1, "h": 1.3, "l": 0.7, "c": 1.0, "volume": 100},
        ]
        self.assertTrue(
            self.oa.is_entry_blocked_by_recent_candles("long", candles)
        )

    def test_allows_same_side(self):
        os.environ["REV_BLOCK_BARS"] = "1"
        os.environ["TAIL_RATIO_BLOCK"] = "2.0"
        os.environ["VOL_SPIKE_PERIOD"] = "1"
        candles = [
            {"o": 1.0, "h": 1.2, "l": 0.8, "c": 1.1, "volume": 100},
            {"o": 1.0, "h": 1.0, "l": 1.0, "c": 1.0, "volume": 100},
        ]
        self.assertFalse(
            self.oa.is_entry_blocked_by_recent_candles("long", candles)
        )


if __name__ == "__main__":
    unittest.main()
