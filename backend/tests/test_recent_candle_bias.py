import os
import sys
import types
import importlib
import unittest

class TestRecentCandleBias(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._mods = []

        def add(name: str, mod: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._mods.append(name)

        pandas_stub = types.ModuleType("pandas")
        add("pandas", pandas_stub)
        add("requests", types.ModuleType("requests"))
        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add("openai", openai_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)
        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = "gpt"
        add("backend.utils.openai_client", oc)

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        os.environ.pop("VOL_SPIKE_PERIOD", None)
        os.environ.pop("REV_BLOCK_BARS", None)
        os.environ.pop("TAIL_RATIO_BLOCK", None)

    def _candle(self, o, c, h, l, v):
        return {"mid": {"o": str(o), "c": str(c), "h": str(h), "l": str(l)}, "volume": v, "complete": True}

    def test_blocks_on_opposite_volume_spike(self):
        candles = [
            self._candle(1.00, 1.01, 1.02, 0.99, 100),
            self._candle(1.01, 0.98, 1.02, 0.97, 500),
            self._candle(0.98, 0.97, 0.99, 0.90, 600),
        ]
        os.environ["VOL_SPIKE_PERIOD"] = "2"
        os.environ["REV_BLOCK_BARS"] = "1"
        os.environ["TAIL_RATIO_BLOCK"] = "5"
        importlib.reload(self.oa)
        self.assertTrue(self.oa.is_entry_blocked_by_recent_candles("long", candles))

    def test_not_block_without_signal(self):
        candles = [
            self._candle(1.00, 1.01, 1.02, 0.99, 100),
            self._candle(1.01, 1.02, 1.03, 1.00, 110),
        ]
        os.environ["VOL_SPIKE_PERIOD"] = "1"
        os.environ["REV_BLOCK_BARS"] = "1"
        os.environ["TAIL_RATIO_BLOCK"] = "3"
        importlib.reload(self.oa)
        self.assertFalse(self.oa.is_entry_blocked_by_recent_candles("long", candles))

if __name__ == "__main__":
    unittest.main()
