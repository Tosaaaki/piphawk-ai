import importlib
import unittest


def _c(p):
    return {"mid": {"o": str(p), "h": str(p + 0.05), "l": str(p - 0.05), "c": str(p)}}


class TestExtensionBlock(unittest.TestCase):
    def setUp(self):
        import backend.filters.extension_block as eb
        importlib.reload(eb)
        self.eb = eb

    def _make_candles(self, prices):
        return [_c(p) for p in prices]

    def test_block_true(self):
        candles = self._make_candles([1.0] * 19 + [1.2])
        self.assertTrue(self.eb.extension_block(candles, 1.5))

    def test_block_false(self):
        candles = self._make_candles([1.0] * 19 + [1.05])
        self.assertFalse(self.eb.extension_block(candles, 1.5))


if __name__ == "__main__":
    unittest.main()
