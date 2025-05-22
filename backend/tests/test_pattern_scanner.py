import os
import sys
import types
import importlib
import unittest

class FakeSeries:
    def __init__(self, data, index=None):
        if isinstance(data, (list, tuple)):
            self._data = list(data)
        else:
            if index is None:
                raise TypeError("index required when scalar data provided")
            self._data = [data for _ in index]
        self.index = list(range(len(self._data))) if index is None else list(index)
        class _ILoc:
            def __init__(self, outer):
                self._outer = outer
            def __getitem__(self, idx):
                return self._outer._data[idx]
            def __setitem__(self, idx, value):
                self._outer._data[idx] = value
        self.iloc = _ILoc(self)
    def shift(self, n):
        if n > 0:
            return FakeSeries([None]*n + self._data[:-n], index=self.index)
        if n < 0:
            return FakeSeries(self._data[-n:] + [None]*(-n), index=self.index)
        return FakeSeries(self._data[:], index=self.index)
    def abs(self):
        return FakeSeries([abs(x) if x is not None else None for x in self._data], index=self.index)
    def __sub__(self, other):
        if isinstance(other, FakeSeries):
            return FakeSeries([a - b if a is not None and b is not None else None for a, b in zip(self._data, other._data)], index=self.index)
        return FakeSeries([a - other if a is not None else None for a in self._data], index=self.index)
    def __truediv__(self, other):
        if isinstance(other, FakeSeries):
            return FakeSeries([a / b if a is not None and b not in (0, None) else None for a, b in zip(self._data, other._data)], index=self.index)
        return FakeSeries([a / other if a is not None and other not in (0, None) else None for a in self._data], index=self.index)
    def fillna(self, value):
        return FakeSeries([value if x is None else x for x in self._data], index=self.index)
    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self._data[idx]
        return self._data[idx]
    def __len__(self):
        return len(self._data)

class FakeDataFrame:
    def __init__(self, data):
        self._cols = {k: FakeSeries(v) for k, v in data.items()}
        self.index = list(range(len(next(iter(self._cols.values()))._data)))
    def __getitem__(self, key):
        return self._cols[key]
    def __len__(self):
        return len(self.index)

class FakePandas(types.ModuleType):
    def __init__(self):
        super().__init__("pandas")
        self.Series = FakeSeries
        self.DataFrame = FakeDataFrame
    def option_context(self, *a, **k):
        class Ctx:
            def __enter__(self):
                pass
            def __exit__(self, exc_type, exc, tb):
                pass
        return Ctx()

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
        self.assertEqual(self.ps.scan_all(data, ["double_bottom"]), "double_bottom")

    def test_head_and_shoulders(self):
        data = [
            {"o":1.0,"h":1.1,"l":0.9,"c":1.0},
            {"o":1.0,"h":1.3,"l":0.95,"c":1.1},
            {"o":1.1,"h":1.5,"l":0.9,"c":1.3},
            {"o":1.3,"h":1.3,"l":1.0,"c":1.2},
            {"o":1.2,"h":1.0,"l":0.8,"c":0.9},
        ]
        self.assertEqual(self.ps.scan_all(data, ["head_and_shoulders"]), "head_and_shoulders")

    def test_double_top(self):
        data = [
            {"o":1.0,"h":1.4,"l":0.9,"c":1.3},
            {"o":1.3,"h":1.4,"l":1.2,"c":1.3},
            {"o":1.3,"h":1.2,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.4,"l":1.1,"c":1.3},
            {"o":1.3,"h":1.1,"l":0.8,"c":0.9},
        ]
        self.assertEqual(self.ps.scan_all(data, ["double_top"]), "double_top")

    def test_pattern_names_filter(self):
        data = [
            {"o":1.2,"h":1.25,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.3,"l":1.1,"c":1.2},
            {"o":1.2,"h":1.24,"l":1.0,"c":1.1},
            {"o":1.1,"h":1.35,"l":1.1,"c":1.3},
        ]
        self.assertIsNone(self.ps.scan_all(data, ["double_top"]))

    def test_scan_multi_timeframes(self):
        data_bottom = [
            {"o": 1.2, "h": 1.25, "l": 1.0, "c": 1.1},
            {"o": 1.1, "h": 1.3, "l": 1.1, "c": 1.2},
            {"o": 1.2, "h": 1.24, "l": 1.0, "c": 1.1},
            {"o": 1.1, "h": 1.35, "l": 1.1, "c": 1.3},
        ]
        data_top = [
            {"o": 1.0, "h": 1.4, "l": 0.9, "c": 1.3},
            {"o": 1.3, "h": 1.4, "l": 1.2, "c": 1.3},
            {"o": 1.3, "h": 1.2, "l": 1.0, "c": 1.1},
            {"o": 1.1, "h": 1.4, "l": 1.1, "c": 1.3},
            {"o": 1.3, "h": 1.1, "l": 0.8, "c": 0.9},
        ]
        result = self.ps.scan({"M1": data_bottom, "M5": data_top}, ["double_bottom", "double_top"])
        self.assertEqual(result, {"M1": "double_bottom", "M5": "double_top"})

        result2 = self.ps.scan({"M1": data_bottom, "M5": data_top}, ["double_top"])
        self.assertEqual(result2, {"M1": None, "M5": "double_top"})

if __name__ == "__main__":
    unittest.main()
