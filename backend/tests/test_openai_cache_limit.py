import importlib
import json
import os
import sys
import types
import unittest


class TestOpenAICacheLimit(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ["OPENAI_CACHE_MAX"] = "3"
        os.environ["MAX_AI_CALLS_PER_LOOP"] = "100"
        self._modules = []

        def add(name: str, module: types.ModuleType):
            sys.modules[name] = module
            self._modules.append(name)

        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                self.chat = types.SimpleNamespace(
                    completions=types.SimpleNamespace(create=self._create)
                )

            @staticmethod
            def _create(model=None, messages=None, max_tokens=None, temperature=None, response_format=None):
                content = messages[1]["content"]
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps({"echo": content})))]
                )

        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add("openai", openai_stub)

        import backend.utils.openai_client as oc
        importlib.reload(oc)
        self.oc = oc

    def tearDown(self):
        for name in self._modules:
            sys.modules.pop(name, None)
        for k in ["OPENAI_API_KEY", "OPENAI_CACHE_MAX", "MAX_AI_CALLS_PER_LOOP"]:
            os.environ.pop(k, None)

    def test_cache_evicts_oldest(self):
        for i in range(4):
            self.oc.ask_openai(f"p{i}")
        keys = list(self.oc._cache.keys())
        self.assertEqual(len(keys), 3)
        prompts = [k[2] for k in keys]
        self.assertEqual(prompts, ["p1", "p2", "p3"])

if __name__ == "__main__":
    unittest.main()
