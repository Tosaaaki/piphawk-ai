import importlib
import sys
import types
import unittest


class TestCandleFetcherTimeout(unittest.TestCase):
    def setUp(self):
        self._added = []

        def add(name: str, mod: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = mod
                self._added.append(name)

        req = types.ModuleType("requests")

        class Timeout(Exception):
            pass

        class RequestException(Exception):
            pass

        req.Timeout = Timeout
        req.RequestException = RequestException

        def get(*a, **k):
            raise Timeout()

        req.get = get
        add("requests", req)

        # also stub pandas to prevent import errors elsewhere if needed
        add("pandas", types.ModuleType("pandas"))

        import backend.market_data.candle_fetcher as cf
        importlib.reload(cf)
        self.cf = cf

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_timeout_returns_empty_list(self):
        res = self.cf.fetch_candles("USD_JPY")
        self.assertEqual(res, [])


if __name__ == "__main__":
    unittest.main()
