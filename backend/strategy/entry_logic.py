from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
from backend.orders.order_manager import OrderManager
from backend.logs.log_manager import log_trade
try:
    from backend.filters.false_break_filter import should_skip as false_break_skip
except ModuleNotFoundError:  # pragma: no cover - fallback for optional import
    def false_break_skip(*_a, **_k):
        return False
try:
    from backend.filters.trend_pullback import should_enter_long as trend_pb_ok
except ModuleNotFoundError:  # pragma: no cover
    def trend_pb_ok(*_a, **_k):
        return True
try:
    from backend.filters.breakout_entry import should_enter_breakout
except ModuleNotFoundError:  # pragma: no cover
    def should_enter_breakout(*_a, **_k):
        return False
try:
    from backend.filters.extension_block import extension_block
except ModuleNotFoundError:  # pragma: no cover
    def extension_block(*_a, **_k):
        return False
from backend.risk_manager import (
    validate_rrr,
    validate_sl,
    calc_min_sl,
    get_recent_swing_diff,
    is_high_vol_session,
)
from datetime import datetime
from backend.utils import env_loader
import logging
import json
import uuid
# optional helper; fallback stub if module is absent
try:
    from backend.utils.oanda_client import get_pending_entry_order  # type: ignore
except ModuleNotFoundError:
    def get_pending_entry_order(instrument: str):
        return None

# env_loader automatically loads default env files at import time

order_manager = OrderManager()

# In‑memory cache: entry_uuid -> {"instrument": str, "order_id": str, "ts": int}
_pending_limits: dict[str, dict] = {}

# 逆張りエントリー機能の有効/無効フラグ
PEAK_ENTRY_ENABLED = (
    env_loader.get_env("PEAK_ENTRY_ENABLED", "false").lower() == "true"
)

def pullback_limit(side: str, price: float, offset_pips: float) -> float:
    """Return limit price offset by given pips in the direction of a pullback."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    return price - offset_pips * pip_size if side == "long" else price + offset_pips * pip_size


def calculate_pullback_offset(indicators: dict, market_cond: dict | None) -> float:
    """Return dynamic pullback offset in pips.

    The base value comes from ``PULLBACK_LIMIT_OFFSET_PIPS`` and is adjusted
    according to the latest ATR value and trend strength (ADX).
    """
    offset = float(env_loader.get_env("PULLBACK_LIMIT_OFFSET_PIPS", "2"))
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))

        atr_series = indicators.get("atr")
        if atr_series is not None and len(atr_series):
            atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            atr_pips = float(atr_val) / pip_size
            ratio = float(env_loader.get_env("PULLBACK_ATR_RATIO", "0.5"))
            offset = offset + atr_pips * ratio

        adx_series = indicators.get("adx")
        if (
            market_cond
            and market_cond.get("market_condition") == "trend"
            and adx_series is not None
            and len(adx_series)
        ):
            adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
            if float(adx_val) >= 30:
                offset *= 1.5
            elif float(adx_val) < 20:
                offset *= 0.7
    except Exception as exc:
        logging.debug(f"[calculate_pullback_offset] failed: {exc}")

    return offset


def process_entry(
    indicators,
    candles,
    market_data,
    market_cond: dict | None = None,
    strategy_params=None,
    *,
    higher_tf: dict | None = None,
    patterns: list[str] | None = None,
    pattern_names: dict[str, str | None] | None = None,
    candles_dict: dict[str, list] | None = None,
    tf_align: str | None = None,
    indicators_multi: dict[str, dict] | None = None,
    allow_delayed_entry: bool | None = None,
):
    """
    Ask OpenAI whether to enter a trade.

    Args:
        indicators: dict of calculated indicators
        candles   : recent candle list (passed through, not used here—kept for API consistency)
        market_data: latest tick data (dict from OANDA)
        market_cond: output of get_market_condition()  e.g. {"market_condition":"trend","trend_direction":"long"}
        strategy_params: optional dict to pass extra parameters / overrides
        indicators_multi: multi-timeframe indicators for alignment adjustment

    Returns:
        True if an entry was placed, False otherwise.
    """
    # If the caller did not pass a dict (JobRunner passes candles), fall back to an empty dict
    if not isinstance(strategy_params, dict):
        strategy_params = {}

    if allow_delayed_entry is None:
        allow_delayed_entry = (
            env_loader.get_env("ALLOW_DELAYED_ENTRY", "false").lower() == "true"
        )

    # ------------------------------------------------------------
    #  Chart pattern scan (local) --------------------------------
    # ------------------------------------------------------------
    if candles_dict is None:
        candles_dict = {"M5": candles}
    else:
        candles_dict = {k.upper(): v for k, v in candles_dict.items()}
        candles_dict.setdefault("M5", candles)

    detected = {} if pattern_names is None else dict(pattern_names)
    try:
        from backend.strategy.pattern_scanner import scan_all

        tfs = [
            tf.strip().upper()
            for tf in env_loader.get_env("PATTERN_TFS", "M1,M5").split(",")
            if tf.strip()
        ]
        for tf in tfs:
            data_tf = candles_dict.get(tf)
            if data_tf:
                detected[tf] = scan_all(data_tf, patterns)
            elif tf not in detected:
                detected[tf] = None
    except Exception as exc:
        logging.debug(f"[process_entry] pattern scan failed: {exc}")

    # ------------------------------------------------------------
    #  Step 1: call unified LLM helper
    # ------------------------------------------------------------
    import importlib
    oa = importlib.import_module("backend.strategy.openai_analysis")

    indicators_multi = {"M5": indicators} if indicators_multi is None else {k.upper(): v for k, v in indicators_multi.items()}
    plan = oa.get_trade_plan(
        market_data,
        indicators_multi,
        candles_dict,
        patterns=patterns,
        detected_patterns=detected,
        allow_delayed_entry=allow_delayed_entry,
    )

    # Raw JSON for audit log
    ai_raw = json.dumps(plan, ensure_ascii=False)
    logging.info(f"AI trade plan raw: {ai_raw}")

    entry_info = plan.get("entry", {})
    risk_info = plan.get("risk", {})

    side = entry_info.get("side", "no").lower()
    mode = entry_info.get("mode", "market")
    limit_price = entry_info.get("limit_price")
    valid_sec = int(
        entry_info.get("valid_for_sec", env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))
    )

    is_break = market_cond and market_cond.get("market_condition") == "break"
    if is_break:
        direction = market_cond.get("break_direction")
        if direction == "up":
            side = "long"
        elif direction == "down":
            side = "short"
        mode = "market"
        limit_price = None

    if side not in ("long", "short"):
        logging.info("AI says no trade entry → early exit")
        return False

    if PEAK_ENTRY_ENABLED:
        try:
            from backend.strategy.signal_filter import detect_peak_reversal
            m5 = candles_dict.get("M5", candles)
            if detect_peak_reversal(m5, side):
                side = "short" if side == "long" else "long"
                logging.info(f"Peak reversal detected → side flipped to {side}")
        except Exception as exc:
            logging.debug(f"[process_entry] peak reversal check failed: {exc}")

    if tf_align:
        try:
            from analysis.signal_filter import is_multi_tf_aligned
            align = is_multi_tf_aligned(indicators_multi, ai_side=side)
            if align and side != align:
                logging.info(
                    f"AI side {side} realigned to {align} by multi‑TF check"
                )
                side = align
            elif align is None and env_loader.get_env(
                "ALIGN_STRICT", env_loader.get_env("STRICT_TF_ALIGN", "false")
            ).lower() == "true":
                logging.info("Multi‑TF alignment missing → skip entry")
                return False
        except Exception as exc:
            logging.debug(f"alignment adjust failed: {exc}")
            if env_loader.get_env(
                "ALIGN_STRICT", env_loader.get_env("STRICT_TF_ALIGN", "false")
            ).lower() == "true":
                return False

    try:
        if getattr(oa, "is_entry_blocked_by_recent_candles", lambda *a, **k: False)(side, candles):
            logging.info("Entry blocked by recent candle bias")
            return False
    except Exception as exc:
        logging.debug(f"[process_entry] bias check failed: {exc}")

    # --- extension block filter ----------------------------------
    try:
        ratio = float(env_loader.get_env("EXT_BLOCK_ATR", "0"))
        if ratio > 0:
            m5 = candles_dict.get("M5", candles)
            if extension_block(m5, ratio):
                logging.info("Extension block triggered → skip entry")
                return False
    except Exception as exc:
        logging.debug(f"[process_entry] extension block failed: {exc}")

    # RSI による逆張りブロック
    try:
        rsi_series = indicators.get("rsi")
        if rsi_series is not None and len(rsi_series):
            rsi_val = rsi_series.iloc[-1] if hasattr(rsi_series, "iloc") else rsi_series[-1]
            os_thresh = float(env_loader.get_env("RSI_OVERSOLD_BLOCK", "35"))
            ob_thresh = float(env_loader.get_env("RSI_OVERBOUGHT_BLOCK", "65"))
            if side == "short" and rsi_val < os_thresh:
                logging.info(
                    f"RSI {rsi_val:.1f} < {os_thresh} → Sell 禁止"
                )
                return False
            if side == "long" and rsi_val > ob_thresh:
                logging.info(
                    f"RSI {rsi_val:.1f} > {ob_thresh} → Buy 禁止"
                )
                return False
    except Exception as exc:
        logging.debug(f"[process_entry] oversold filter failed: {exc}")

    # --- false break filter -----------------------------------------
    try:
        lookback = int(env_loader.get_env("FALSE_BREAK_LOOKBACK", "5"))
        ratio = float(env_loader.get_env("FALSE_BREAK_RATIO", "0.5"))
        m5 = candles_dict.get("M5", candles)
        if false_break_skip(m5, lookback, ratio):
            logging.info("False break detected → skip entry")
            return False
    except Exception as exc:
        logging.debug(f"[process_entry] false-break filter failed: {exc}")

    breakout_entry = False
    try:
        breakout_entry = should_enter_breakout(candles_dict.get("M5", candles), indicators)
    except Exception as exc:
        logging.debug(f"[process_entry] breakout check failed: {exc}")

    try:
        if side == "long" and not breakout_entry and not trend_pb_ok(indicators, candles_dict.get("M5", candles)):
            logging.info("Trend pullback conditions not met → skip entry")
            return False
    except Exception as exc:
        logging.debug(f"[process_entry] trend-pullback check failed: {exc}")

    # --- dynamic pullback threshold ---------------------------------
    pullback_needed = None
    if not is_break:
        try:
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            atr_series = indicators.get("atr")
            bb_upper = indicators.get("bb_upper")
            bb_lower = indicators.get("bb_lower")
            atr_val = atr_series.iloc[-1] if atr_series is not None else None
            if atr_val is not None:
                atr_val = float(atr_val)
            bw_val = None
            if bb_upper is not None and bb_lower is not None:
                bw_val = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
            atr_pips = atr_val / pip_size if atr_val is not None else 0.0
            bw_pips = bw_val / pip_size if bw_val is not None else 0.0
            class _OneVal:
                def __init__(self, val):
                    class _IL:
                        def __getitem__(self, idx):
                            return val
                    self.iloc = _IL()

            noise_series = _OneVal(max(atr_pips, bw_pips))
            highs = []
            lows = []
            for c in candles[-20:]:
                if 'mid' in c:
                    highs.append(float(c['mid']['h']))
                    lows.append(float(c['mid']['l']))
                else:
                    highs.append(float(c.get('h')))
                    lows.append(float(c.get('l')))
            recent_high = max(highs) if highs else 0.0
            recent_low = min(lows) if lows else 0.0
            pullback_needed = calculate_dynamic_pullback({**indicators, 'noise': noise_series}, recent_high, recent_low)
        except Exception:
            pass

    if isinstance(market_data, dict):
        instrument = market_data["prices"][0]["instrument"]
        bid = float(market_data["prices"][0]["bids"][0]["price"])
        ask = float(market_data["prices"][0]["asks"][0]["price"])
    else:
        instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
        bid = ask = None

    if mode == "market" and not is_break:
        price_ref = bid if side == "long" else ask
        offset = 0.0
        if higher_tf and price_ref is not None:
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            sup_pips = float(env_loader.get_env("PIVOT_SUPPRESSION_PIPS", "15"))
            base_pullback = float(env_loader.get_env("PULLBACK_PIPS", "3"))
            pullback = pullback_needed if pullback_needed is not None else base_pullback
            tfs = [
                tf.strip().upper()
                for tf in env_loader.get_env("PIVOT_SUPPRESSION_TFS", "D").split(",")
                if tf.strip()
            ]
            for tf in tfs:
                pivot = higher_tf.get(f"pivot_{tf.lower()}")
                if pivot is None:
                    continue
                if abs((price_ref - pivot) / pip_size) <= sup_pips:
                    offset = pullback
                    break
        if offset == 0.0:
            offset = calculate_pullback_offset(indicators, market_cond)
        if pullback_needed is not None:
            offset = max(offset, pullback_needed)
        if offset and price_ref is not None:
            limit_price = pullback_limit(side, price_ref, offset)

    # ------------------------------------------------------------
    #  Detect narrow-range market (Bollinger band width < threshold)
    # ------------------------------------------------------------
    narrow_range = False
    if not is_break:
        try:
            bb_upper = indicators.get("bb_upper")
            bb_lower = indicators.get("bb_lower")
            if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
                bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
                narrow_range = bw_pips < bw_thresh
        except Exception as exc:
            logging.debug(f"[process_entry] narrow-range detection failed: {exc}")

    # ------------------------------------------------------------
    #  Range market handling: switch to LIMIT if near BB center
    # ------------------------------------------------------------
    if not is_break:
        try:
            if (
                (market_cond and market_cond.get("market_condition") == "range")
                or narrow_range
            ) and bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                price_ref = bid if side == "long" else ask
                if price_ref is not None:
                    center = (bb_upper.iloc[-1] + bb_lower.iloc[-1]) / 2
                    distance_pips = abs(price_ref - center) / pip_size
                    offset_threshold = float(
                        env_loader.get_env("RANGE_ENTRY_OFFSET_PIPS", "3")
                    )
                    if distance_pips <= offset_threshold:
                        target = bb_lower.iloc[-1] if side == "long" else bb_upper.iloc[-1]
                        offset_pips = abs(price_ref - target) / pip_size
                        limit_price = pullback_limit(side, price_ref, offset_pips)
                        mode = "limit"
        except Exception as exc:
            logging.debug(f"[process_entry] range-limit conversion failed: {exc}")

    # ------------------------------------------------------------
    #  Spread cap: convert market entry to LIMIT when spread is wide
    # ------------------------------------------------------------
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        max_spread = float(env_loader.get_env("MAX_SPREAD_PIPS", "0"))
        if max_spread > 0 and bid is not None and ask is not None and mode == "market":
            spread_pips = (ask - bid) / pip_size
            if spread_pips > max_spread:
                limit_price = bid if side == "long" else ask
                mode = "limit"
                logging.info(
                    f"Spread {spread_pips:.1f} exceeds {max_spread} → switching to LIMIT"
                )
    except Exception as exc:  # pragma: no cover - edge case logging
        logging.debug(f"[process_entry] spread check failed: {exc}")

    if mode == "wait":
        logging.info("AI suggests WAIT – re‑evaluate next loop.")
        return False

    tp_pips = risk_info.get("tp_pips")
    sl_pips = risk_info.get("sl_pips")
    fallback_tp = None

    min_sl = float(env_loader.get_env("MIN_SL_PIPS", "0"))
    fallback_sl = None
    atr_pips = None
    dynamic_min_sl = 0.0
    try:
        atr_series = indicators.get("atr")
        if atr_series is not None and len(atr_series):
            if hasattr(atr_series, "iloc"):
                atr_val = float(atr_series.iloc[-1])
            else:
                atr_val = float(atr_series[-1])
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            atr_pips = atr_val / pip_size
            mult_sl = float(env_loader.get_env("ATR_MULT_SL", env_loader.get_env("ATR_SL_MULTIPLIER", "2.0")))
            fallback_sl = atr_pips * mult_sl
            mult_tp = float(env_loader.get_env("ATR_MULT_TP", env_loader.get_env("SHORT_TP_ATR_RATIO", "0.6")))
            fallback_tp = atr_pips * mult_tp
        price_ref = bid if side == "long" else ask
        # SL用ピボットレベル
        pivot_sl_key = "pivot_s1" if side == "long" else "pivot_r1"
        pivot_sl_val = indicators.get(pivot_sl_key)
        if pivot_sl_val is not None and price_ref is not None:
            dist_sl = abs(price_ref - pivot_sl_val) / pip_size
            if fallback_sl is None or dist_sl > fallback_sl:
                fallback_sl = dist_sl
        pivot_key = "pivot_r1" if side == "long" else "pivot_s1"
        pivot_val = indicators.get(pivot_key)
        if pivot_val is not None and price_ref is not None:
            dist = abs(pivot_val - price_ref) / pip_size
            if fallback_tp is None or dist < fallback_tp:
                fallback_tp = dist
        n_target = indicators.get("n_wave_target")
        if n_target is not None and price_ref is not None:
            dist = abs(n_target - price_ref) / pip_size
            if fallback_tp is None or dist < fallback_tp:
                fallback_tp = dist
            # N波ターゲットをSL候補として利用
            if fallback_sl is None or dist > fallback_sl:
                fallback_sl = dist

        # ヒゲ幅平均×2をSL候補に追加
        try:
            wicks = []
            for c in candles[-3:]:
                base = c.get("mid", c)
                high = float(base.get("h"))
                low = float(base.get("l"))
                opn = float(base.get("o", 0))
                cls = float(base.get("c", 0))
                upper = high - max(opn, cls)
                lower = min(opn, cls) - low
                wicks.append((upper + lower) / pip_size)
            if wicks:
                wick_sl = sum(wicks) / len(wicks) * 2
                if fallback_sl is None or wick_sl > fallback_sl:
                    fallback_sl = wick_sl
        except Exception:
            pass
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        if (
            bb_upper is not None
            and bb_lower is not None
            and price_ref is not None
        ):
            if hasattr(bb_upper, "iloc"):
                width = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
            else:
                width = float(bb_upper[-1]) - float(bb_lower[-1])
            width_pips = width / pip_size
            bb_ratio = float(env_loader.get_env("TP_BB_RATIO", "0.6"))
            bb_tp = width_pips * bb_ratio
            if fallback_tp is None or bb_tp < fallback_tp:
                fallback_tp = bb_tp

        # 上位足ピボットとの距離を TP 候補として追加
        if (
            env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
            and higher_tf
            and price_ref is not None
        ):
            for key in ("pivot_h1", "pivot_h4", "pivot_d"):
                pivot_val = higher_tf.get(key)
                if pivot_val is None:
                    continue
                dist = abs(pivot_val - price_ref) / pip_size
                if fallback_tp is None or dist < fallback_tp:
                    fallback_tp = dist

        # 動的SL下限計算
        entry_price = bid if side == "long" else ask
        swing_diff = None
        if entry_price is not None:
            swing_diff = get_recent_swing_diff(candles, side, entry_price, pip_size)
        session_factor = 1.3 if is_high_vol_session() else 1.0
        dynamic_min_sl = calc_min_sl(
            atr_pips,
            swing_diff,
            atr_mult=float(env_loader.get_env("MIN_ATR_MULT", "1.2")),
            swing_buffer_pips=5.0,
            session_factor=session_factor,
        )
    except Exception as exc:
        logging.debug(f"[process_entry] ATR-based SL calc failed: {exc}")

    if tp_pips is None:
        tp_pips = fallback_tp if fallback_tp is not None else float(env_loader.get_env("INIT_TP_PIPS", "30"))
    else:
        try:
            tp_pips = float(tp_pips)
        except Exception:
            tp_pips = float(env_loader.get_env("INIT_TP_PIPS", "30"))

    if sl_pips is None:
        sl_pips = fallback_sl if fallback_sl is not None else float(env_loader.get_env("INIT_SL_PIPS", "20"))
    else:
        try:
            sl_pips = float(sl_pips)
        except Exception:
            sl_pips = float(env_loader.get_env("INIT_SL_PIPS", "20"))

    if fallback_sl is not None:
        sl_pips = max(sl_pips, fallback_sl)
    try:
        sl_pips = max(sl_pips, dynamic_min_sl)
    except Exception:
        pass
    if sl_pips < min_sl:
        sl_pips = min_sl
    try:
        if env_loader.get_env("ENFORCE_RRR", "false").lower() == "true":
            min_rrr = float(env_loader.get_env("MIN_RRR", "0.8"))
            if not validate_rrr(tp_pips, sl_pips, min_rrr):
                tp_pips = sl_pips * min_rrr
    except Exception:
        pass

    # マルチTFが逆方向の場合のTP短縮
    try:
        if isinstance(strategy_params, dict):
            ratio = strategy_params.get("tp_ratio")
            if ratio:
                tp_pips = tp_pips * float(ratio)
    except Exception:
        pass
    try:
        min_atr_mult = float(env_loader.get_env("MIN_ATR_MULT", "1.0"))
        if atr_pips is not None:
            validate_sl(tp_pips, sl_pips, atr_pips, min_atr_mult)
    except Exception:
        pass
    logging.info(f"AI Entry {side} – tp={tp_pips}  sl={sl_pips} (pips)")

    if mode == "limit":
        if limit_price is None:
            logging.warning("LIMIT mode but no limit_price → skip entry.")
            return False

        # Check if a similar pending order already exists
        open_orders = (
            order_manager.get_open_orders(instrument, side)
            if hasattr(order_manager, "get_open_orders")
            else []
        )
        if open_orders:
            logging.info("Existing pending order found – skip entry.")
            return False
        existing = get_pending_entry_order(instrument)
        if existing:
            logging.info("Pending LIMIT order already exists – skip new limit placement.")
            return False

        entry_uuid = str(uuid.uuid4())[:8]
        params_limit = {
            "instrument": instrument,
            "side": side,
            "tp_pips": tp_pips,
            "sl_pips": sl_pips,
            "mode": "limit",
            "limit_price": limit_price,
            "entry_uuid": entry_uuid,
            "valid_for_sec": valid_sec,
            "ai_response": ai_raw,
            "market_cond": market_cond,
        }
        result = order_manager.enter_trade(
            side=side,
            lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
            market_data=market_data,
            strategy_params=params_limit,
            force_limit_only=False,
        )
        if result:
            _pending_limits[entry_uuid] = {
                "instrument": instrument,
                "order_id": result.get("order_id"),
                "ts": int(datetime.utcnow().timestamp()),
                "limit_price": limit_price,
                "side": side,
                "retry_count": 0,
            }
        return bool(result)
    else:
        # --- MARKET order path ---
        if hasattr(order_manager, "get_open_orders") and order_manager.get_open_orders(instrument, side):
            logging.info("Existing pending order found – skip market entry.")
            return False
        params = {
            **strategy_params,
            "instrument": instrument,
            "side": side,
            "tp_pips": tp_pips,
            "sl_pips": sl_pips,
            "mode": "market",
            "limit_price": limit_price,
            "ai_response": ai_raw,
            "market_cond": market_cond,
        }

    trade_result = order_manager.enter_trade(
        side=side,
        lot_size=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
        market_data=market_data,
        strategy_params=params,
        force_limit_only=False
    )

    if trade_result and mode == "market":
        instrument = params["instrument"]
        lot_size = float(env_loader.get_env("TRADE_LOT_SIZE", "1.0"))
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_price = float(market_data['prices'][0]['bids'][0]['price'])
        entry_time = datetime.utcnow().isoformat()
        rrr = None
        try:
            if tp_pips is not None and sl_pips not in (None, 0):
                rrr = float(tp_pips) / float(sl_pips)
        except Exception:
            rrr = None
        log_trade(
            instrument,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            ai_reason=ai_raw,
            ai_response=ai_raw,
            tp_pips=tp_pips,
            sl_pips=sl_pips,
            rrr=rrr,
        )

    return True
