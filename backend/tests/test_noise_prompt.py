import importlib
import os
import sys
import types
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

class TestNoiseInPrompt(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._added_modules = []
        def add_module(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added_modules.append(name)
        add_module("pandas", types.ModuleType("pandas"))
        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add_module("openai", openai_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add_module("dotenv", dotenv_stub)
        add_module("requests", types.ModuleType("requests"))
        add_module("numpy", types.ModuleType("numpy"))
        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)

    def test_prompt_includes_noise(self):
        captured = []
        self.oa.ask_openai = lambda prompt, **k: (captured.append(prompt) or '{"entry": {"side": "no"}}')
        indicators = {
            "bb_upper": FakeSeries([1.1]),
            "bb_lower": FakeSeries([1.0]),
            "atr": FakeSeries([0.001]),
        }
        self.oa.get_trade_plan({}, {"M5": indicators}, {"M5": []})
        self.assertTrue(captured)
        self.assertIn("Estimated Noise", captured[0])

if __name__ == "__main__":
    unittest.main()
