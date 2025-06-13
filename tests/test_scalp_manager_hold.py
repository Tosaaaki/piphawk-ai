import os

# OANDA 環境変数をダミー設定
os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")

import execution.scalp_manager as sm


class FakeSeries:
    def __init__(self, val):
        class _IL:
            def __getitem__(self, idx):
                return val

        self.iloc = _IL()
        self._val = val

    def __getitem__(self, idx):
        return self._val


def test_dynamic_hold_seconds_exact(monkeypatch):
    candle = {"mid": {"h": "1.0", "l": "0.9", "c": "0.95"}, "complete": True}
    fetch_func = lambda *a, **k: [candle] * 30
    atr_func = lambda *a, **k: FakeSeries(0.05)
    monkeypatch.setattr(sm, "get_pip_size", lambda i: 0.01)
    monkeypatch.setenv("HOLD_TIME_MIN", "10")
    monkeypatch.setenv("HOLD_TIME_MAX", "1000")

    hold = sm.get_dynamic_hold_seconds(
        "USD_JPY",
        fetch_candles_func=fetch_func,
        calculate_atr_func=atr_func,
    )
    expected = int(0.05 / 0.01 / 0.006)
    assert hold == expected

