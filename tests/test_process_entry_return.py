import os
import types

os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")

from backend.strategy import entry_logic


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
        return self._data[idx]

    def __len__(self):
        return len(self._data)


def test_process_entry_returns_false(monkeypatch):
    monkeypatch.setattr(entry_logic.order_manager, "enter_trade", lambda *a, **k: None)
    monkeypatch.setattr(entry_logic, "decide_trade_mode", lambda *_a, **_k: "trend")
    monkeypatch.setattr(entry_logic, "decide_trade_mode_detail", lambda *_a, **_k: ("trend", 0.0, {}))
    monkeypatch.setattr(
        "backend.strategy.openai_analysis.get_trade_plan",
        lambda *a, **k: {"entry": {"side": "long", "mode": "market"}, "risk": {"tp_pips": 2, "sl_pips": 1}},
    )
    monkeypatch.setattr(
        "backend.strategy.openai_analysis.should_convert_limit_to_market", lambda ctx: True
    )
    monkeypatch.setattr(
        "backend.strategy.openai_analysis.evaluate_exit",
        lambda *a, **k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason=""),
    )
    monkeypatch.setattr("backend.logs.trade_logger.log_trade", lambda *a, **k: None)
    monkeypatch.setattr(
        "backend.strategy.dynamic_pullback.calculate_dynamic_pullback", lambda *a, **k: 0
    )
    monkeypatch.setenv("PIP_SIZE", "0.01")

    indicators = {"atr": FakeSeries([0.1])}
    candles = []
    market_data = {
        "prices": [
            {"instrument": "USD_JPY", "bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}]}
        ]
    }
    result = entry_logic.process_entry(
        indicators, candles, market_data, candles_dict={"M5": candles}, tf_align=None
    )
    assert result is False


def test_process_entry_return_side(monkeypatch):
    monkeypatch.setattr(entry_logic, "decide_trade_mode", lambda *_a, **_k: "trend")
    monkeypatch.setattr(entry_logic, "decide_trade_mode_detail", lambda *_a, **_k: ("trend", 0.0, {}))
    monkeypatch.setattr(
        "backend.strategy.openai_analysis.get_trade_plan",
        lambda *a, **k: {"entry": {"side": "short", "mode": "market"}, "risk": {}}
    )
    monkeypatch.setenv("PIP_SIZE", "0.01")

    indicators = {"atr": FakeSeries([0.1])}
    candles = []
    market_data = {
        "prices": [
            {"instrument": "USD_JPY", "bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}]}
        ]
    }
    side = entry_logic.process_entry(
        indicators,
        candles,
        market_data,
        candles_dict={"M5": candles},
        tf_align=None,
        return_side=True,
    )
    assert side == "short"
