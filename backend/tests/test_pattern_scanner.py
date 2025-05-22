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
        pandas_stub = FakePandas()
        if "pandas" not in sys.modules:
            sys.modules["pandas"] = pandas_stub
            self._added.append("pandas")
        import backend.strategy.pattern_scanner as ps
        importlib.reload(ps)
        self.ps = ps
        data = {
            "open":  [1, 1.8, 2.5, 4.8, 4.0, 4.9, 4.35, 3.0, 2.1, 1.0],
            "high":  [1.2, 2.2, 3.0, 5.0, 4.5, 5.1, 4.4, 3.5, 2.5, 1.1],
            "low":   [0.8, 1.5, 2.2, 4.5, 3.5, 4.7, 4.2, 2.8, 1.9, 0.9],
            "close": [1.0, 2.0, 2.8, 4.9, 4.2, 5.0, 4.3, 3.1, 2.2, 1.1],
        }
        self.df = FakeDataFrame(data)

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_scan_all(self):
        result = self.ps.scan_all(self.df)
        self.assertIn("double_top", result)
        self.assertEqual(len(result["double_top"]), len(self.df.index))

    def test_get_last_pattern_name(self):
        name = self.ps.get_last_pattern_name(self.df)
        self.assertEqual(name, "double_top")

if __name__ == "__main__":
    unittest.main()
