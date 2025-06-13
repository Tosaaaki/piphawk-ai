import importlib
import sys
from types import SimpleNamespace


def test_micro_scalp_on_ai_no(monkeypatch):
    # 環境変数設定
    monkeypatch.setenv("MICRO_SCALP_ENABLED", "true")
    monkeypatch.setenv("SCALP_SUPPRESS_ADX_MAX", "0")
    monkeypatch.setenv("SCALP_TP_PIPS", "2")
    monkeypatch.setenv("SCALP_SL_PIPS", "1")
    monkeypatch.setenv("OANDA_API_KEY", "x")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "x")

    import backend.strategy.entry_logic as el

    # モジュールパッチ
    scalp_mod = SimpleNamespace(get_scalp_plan=lambda *a, **k: {"side": "no"})
    micro_mod = SimpleNamespace(
        get_plan=lambda *a, **k: {
            "enter": True,
            "side": "short",
            "tp_pips": 3,
            "sl_pips": 1,
        }
    )
    md_mod = SimpleNamespace(calc_tick_features=lambda _t: {})

    monkeypatch.setitem(sys.modules, "backend.strategy.openai_scalp_analysis", scalp_mod)
    monkeypatch.setitem(sys.modules, "backend.strategy.openai_micro_scalp", micro_mod)
    monkeypatch.setitem(sys.modules, "backend.market_data", md_mod)

    # OrderManager ダミー
    calls = {}

    class DummyOM:
        def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False):
            calls["side"] = side
            calls["tp_pips"] = strategy_params.get("tp_pips")
            calls["sl_pips"] = strategy_params.get("sl_pips")
            return {"ok": True}

    monkeypatch.setattr(el, "order_manager", DummyOM())

    # 依存関数のスタブ
    monkeypatch.setattr(el, "calc_lot_size", lambda *a, **k: 1.0)
    monkeypatch.setattr(el, "_calc_scalp_tp_sl", lambda *a, **k: (None, None))
    monkeypatch.setattr(el, "_calc_reversion_tp_sl", lambda *a, **k: (None, None))
    monkeypatch.setattr(el, "false_break_skip", lambda *_a, **_k: False)

    indicators = {
        "adx": [25],
        "bb_upper": [1.2],
        "bb_lower": [1.0],
        "atr": [0.1],
        "rsi": [50],
    }
    candle = {"mid": {"c": "1", "h": "1", "l": "1"}, "complete": True}
    candles = [candle] * 20
    market_data = {
        "prices": [{
            "instrument": "USD_JPY",
            "bids": [{"price": "1.0"}],
            "asks": [{"price": "1.01"}],
        }]
    }

    res = el.process_entry(
        indicators,
        candles,
        market_data,
        market_cond={"trend_direction": "long"},
        strategy_params={"ticks": []},
    )

    assert res is True
    assert calls["side"] == "short"
    assert calls["tp_pips"] == 3
    assert calls["sl_pips"] == 1
