import os
import sys
import types
import importlib
import unittest

class TestPatternScanner(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
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
        import backend.strategy.pattern_scanner as ps
        importlib.reload(ps)
        self.ps = ps

    def tearDown(self):
        for name in getattr(self, "_added", []):
            sys.modules.pop(name, None)

    def test_double_bottom(self):
        data = [
            {"o":1.2,"h":1.25,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.3,"l":1.1,"c":1.2},
            {"o":1.2,"h":1.24,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.35,"l":1.1,"c":1.3},
        ]
        self.assertEqual(self.ps.scan_all(data), "double_bottom")

    def test_double_top(self):
        data = [
            {"o":1.0,"h":1.4,"l":0.9,"c":1.3},
            {"o":1.3,"h":1.4,"l":1.2,"c":1.3},
            {"o":1.3,"h":1.2,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.4,"l":1.1,"c":1.3},
            {"o":1.3,"h":1.1,"l":0.8,"c":0.9},
        ]
        self.assertEqual(self.ps.scan_all(data), "double_top")


if __name__ == "__main__":
    unittest.main()
