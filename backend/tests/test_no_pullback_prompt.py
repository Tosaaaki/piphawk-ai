import os
import sys
import types
import importlib
import unittest

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
        if isinstance(idx, slice):
            return self._data[idx]
        if isinstance(idx, int) and idx < 0:
            raise KeyError(idx)
        return self._data[idx]
    def __len__(self):
        return len(self._data)

class TestNoPullbackPrompt(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["ALLOW_NO_PULLBACK_WHEN_ADX"] = "55"
        self._mods = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._mods.append(name)
        add("pandas", types.ModuleType("pandas"))
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
        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_mods", []):
            sys.modules.pop(name, None)
        os.environ.pop("ALLOW_NO_PULLBACK_WHEN_ADX", None)

    def test_prompt_mentions_no_pullback(self):
        captured = []
        self.oa.ask_openai = lambda prompt, **k: (captured.append(prompt) or '{"entry": {"side": "no"}}')
        indicators = {"adx": FakeSeries([60])}
        self.oa.get_trade_plan({}, {"M5": indicators}, {"M5": []})
        self.assertTrue(captured)
        self.assertIn("Pullback not required when ADX is high.", captured[0])

if __name__ == "__main__":
    unittest.main()
