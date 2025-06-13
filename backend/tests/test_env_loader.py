import importlib
import os
import sys
import types
import unittest


class TestEnvLoader(unittest.TestCase):
    def setUp(self):
        self._mods: list[str] = []

        def add(name: str, mod: types.ModuleType) -> None:
            sys.modules[name] = mod
            self._mods.append(name)

        requests_stub = types.ModuleType("requests")
        add("requests", requests_stub)

        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)

        self.env_loader = importlib.import_module("backend.utils.env_loader")

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        os.environ.pop("EMPTY_VAR", None)
        os.environ.pop("MISSING_VAR", None)

    def test_empty_env_returns_default(self):
        os.environ["EMPTY_VAR"] = ""
        self.assertEqual(
            self.env_loader.get_env("EMPTY_VAR", "default"),
            "default",
        )

    def test_missing_env_returns_default(self):
        self.assertEqual(
            self.env_loader.get_env("MISSING_VAR", "fallback"),
            "fallback",
        )
