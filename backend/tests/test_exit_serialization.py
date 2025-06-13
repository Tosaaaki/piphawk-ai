import importlib
import os
import sys
import types
import unittest


class FakeSeries:
    def __init__(self, data):
        self._data = list(data)
    def tolist(self):
        return self._data

class TestExitSerialization(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._mods = []
        def add(name, mod):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._mods.append(name)
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
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
        import backend.strategy.exit_ai_decision as ead
        importlib.reload(ead)
        self.ead = ead

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)

    def test_build_prompt_serializes_series(self):
        ctx = {"foo": FakeSeries([1, 2, 3])}
        prompt = self.ead._build_prompt(ctx)
        self.assertIn('[1,2,3]', prompt)

if __name__ == '__main__':
    unittest.main()
