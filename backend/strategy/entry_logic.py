import importlib

from backend.filters.false_break_filter import should_skip as false_break_skip
from backend.logs.trade_logger import log_trade
from backend.orders.order_manager import OrderManager
from backend.risk_manager import tp_only_condition
from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
from backend.strategy.risk_manager import calc_lot_size
from risk.tp_sl_manager import adjust_sl_for_rr

# trend_pullback filter removed – AI handles pullback assessment

try:
    scalp_mod = importlib.import_module("backend.filters.scalp_entry")
    should_enter_long_scalp = getattr(
        scalp_mod, "should_enter_long", lambda *_a, **_k: True
    )
    should_enter_short_scalp = getattr(
        scalp_mod, "should_enter_short", lambda *_a, **_k: True
    )
except ModuleNotFoundError:  # pragma: no cover

    def should_enter_long_scalp(*_a, **_k):
        return True

    def should_enter_short_scalp(*_a, **_k):
        return True


try:
    from backend.filters.breakout_entry import should_enter_breakout
except ModuleNotFoundError:  # pragma: no cover

    def should_enter_breakout(*_a, **_k):
        logging.debug("breakout_entry module missing -> returning False")
        return False


from backend.filters.extension_block import is_extension

try:

    from backend.filters.h1_level_block import (
        is_near_h1_resistance,
        is_near_h1_support,
    )
except ModuleNotFoundError:  # pragma: no cover

    def is_near_h1_support(*_a, **_k):
        logging.debug("h1_level_block module missing -> assuming not near support")
        return False

    def is_near_h1_resistance(*_a, **_k):
        logging.debug("h1_level_block module missing -> assuming not near resistance")
        return False


import json
import logging
import os
import uuid
from datetime import datetime, timezone

from backend.risk_manager import (
    calc_fallback_tp_sl,
    calc_min_sl,
    get_recent_swing_diff,
    is_high_vol_session,
    validate_rrr,
    validate_rrr_after_cost,
    validate_sl,
)
from backend.utils import env_loader

# signals パッケージはプロジェクト直下にあるため、
# 絶対インポートで確実に読み込む
from piphawk_ai.signals.composite_mode import (
    decide_trade_mode,
    decide_trade_mode_detail,
)

logger = logging.getLogger(__name__)
log_level = env_loader.get_env("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))

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
PEAK_ENTRY_ENABLED = env_loader.get_env("PEAK_ENTRY_ENABLED", "false").lower() == "true"


def pullback_limit(side: str, price: float, offset_pips: float) -> float:
    """Return limit price offset by given pips in the direction of a pullback."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    return (
        price - offset_pips * pip_size
        if side == "long"
        else price + offset_pips * pip_size
    )


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
            atr_val = (
                atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            )
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
            adx_val = (
                adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
            )
            if float(adx_val) >= 30:
                offset *= 1.5
            elif float(adx_val) < 20:
                offset *= 0.7
    except Exception as exc:
        logging.debug(f"[calculate_pullback_offset] failed: {exc}")

    return offset


def _calc_scalp_tp_sl(
    indicators: dict,
    indicators_multi: dict[str, dict] | None,
    tf: str,
    price: float,
    side: str,
    pip_size: float,
) -> tuple[float | None, float | None]:
    """Return TP/SL distances in pips based on Bollinger Bands."""

    src = indicators
    if indicators_multi and isinstance(indicators_multi.get(tf), dict):
        src = indicators_multi[tf]

    bb_upper = src.get("bb_upper")
    bb_lower = src.get("bb_lower")
    if not bb_upper or not bb_lower:
        return None, None

    try:
        up = bb_upper.iloc[-1] if hasattr(bb_upper, "iloc") else bb_upper[-1]
        low = bb_lower.iloc[-1] if hasattr(bb_lower, "iloc") else bb_lower[-1]
    except Exception:
        return None, None

    if side == "long":
        tp = (up - price) / pip_size
        sl = (price - low) / pip_size
    else:
        tp = (price - low) / pip_size
        sl = (up - price) / pip_size

    return max(tp, 0.0), max(sl, 0.0)


def _calc_reversion_tp_sl(indicators: dict, pip_size: float) -> tuple[float | None, float | None]:
    """Return TP/SL using ATR or Bollinger width for scalp reversion."""
    atr_series = indicators.get("atr")
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    atr_pips = None
    width_pips = None
    if atr_series is not None and len(atr_series):
        try:
            atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
            atr_pips = float(atr_val) / pip_size
        except Exception:
            atr_pips = None
    if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
        try:
            up = bb_upper.iloc[-1] if hasattr(bb_upper, "iloc") else bb_upper[-1]
            low = bb_lower.iloc[-1] if hasattr(bb_lower, "iloc") else bb_lower[-1]
            width_pips = (up - low) / pip_size
        except Exception:
            width_pips = None
    noise = 0.0
    if atr_pips is not None:
        noise = max(noise, atr_pips)
    if width_pips is not None:
        noise = max(noise, width_pips)
    if noise == 0.0:
        return None, None
    tp_mult = float(env_loader.get_env("SCALP_REV_TP_MULT", "0.6"))
    sl_mult = float(env_loader.get_env("SCALP_REV_SL_MULT", "1.0"))
    return noise * tp_mult, noise * sl_mult


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
    risk_engine=None,
    return_side: bool | None = False,
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
        return_side   : if True, return only the AI-determined side without
                        placing any order

    Returns:
        True if an entry was placed, False otherwise. When ``return_side`` is
        True, return the side string ("long"/"short") determined by the AI
        without executing an order.
    """
    # If the caller did not pass a dict (JobRunner passes candles), fall back to an empty dict
    if not isinstance(strategy_params, dict):
        strategy_params = {}

    if allow_delayed_entry is None:
        allow_delayed_entry = (
            env_loader.get_env("ALLOW_DELAYED_ENTRY", "true").lower() == "true"
        )

    forced_entry = False
    # フィルター通過後は必ずエントリーするため常に True
    force_entry_after_ai = True
    use_dynamic_risk = (
        env_loader.get_env("FALLBACK_DYNAMIC_RISK", "false").lower() == "true"
    )

    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    spread_pips = None
    try:
        if isinstance(market_data, dict):
            bid = float(market_data["prices"][0]["bids"][0]["price"])
            ask = float(market_data["prices"][0]["asks"][0]["price"])
            spread_pips = (ask - bid) / pip_size
    except Exception:
        spread_pips = None

    noise_pips = None
    try:
        atr_series = indicators.get("atr")
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        atr_val = None
        if atr_series is not None and len(atr_series):
            atr_val = (
                float(atr_series.iloc[-1]) if hasattr(atr_series, "iloc") else float(atr_series[-1])
            )
        bw_val = None
        if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            bw_val = float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1])
        atr_pips = atr_val / pip_size if atr_val is not None else 0.0
        bw_pips = bw_val / pip_size if bw_val is not None else 0.0
        noise_pips = max(atr_pips, bw_pips)
    except Exception:
        noise_pips = None

    # ADX からトレードモードを判定
    adx_series = indicators.get("adx")
    adx_val = None
    if adx_series is not None and len(adx_series):
        adx_val = (
            float(adx_series.iloc[-1])
            if hasattr(adx_series, "iloc")
            else float(adx_series[-1])
        )
    trade_mode = decide_trade_mode(indicators)
    logging.info("Trade mode decided: %s", trade_mode)
    strong_trend_mode = trade_mode == "strong_trend"
    # モードによらずスキャル条件を評価する
    scalp_mode = adx_val is not None
    adx_max = float(env_loader.get_env("SCALP_SUPPRESS_ADX_MAX", "0"))
    if adx_val is not None and adx_max > 0 and adx_val > adx_max:
        scalp_mode = False
    os.environ["SCALP_MODE"] = "true" if scalp_mode else "false"

    # スキャル専用の条件
    logging.info("SCALP_MODE is %s", "ON" if scalp_mode else "OFF")
    if scalp_mode and env_loader.get_env("SCALP_OVERRIDE_RANGE", "false").lower() == "true":
        if market_cond is not None:
            market_cond["market_condition"] = "trend"
            logging.info("SCALP_OVERRIDE_RANGE active – regime forced to trend")

    if scalp_mode:
        mode = "market"
        limit_price = None
        try:
            import importlib

            scalp_ai = importlib.import_module(
                "backend.strategy.openai_scalp_analysis"
            )
            plan = scalp_ai.get_scalp_plan(
                indicators,
                candles,
                higher_tf_direction=(market_cond or {}).get("trend_direction"),
            )

            ai_side = plan.get("side")
            if ai_side not in ("long", "short"):
                micro_plan = None
                if env_loader.get_env("MICRO_SCALP_ENABLED", "false").lower() == "true":
                    from backend.market_data import calc_tick_features

                    ticks = []
                    if isinstance(strategy_params, dict):
                        ticks = strategy_params.get("ticks") or []
                    mscalp = importlib.import_module(
                        "backend.strategy.openai_micro_scalp"
                    )
                    feats = calc_tick_features(ticks)
                    micro_plan = mscalp.get_plan(feats)

                if micro_plan and micro_plan.get("enter"):
                    plan = micro_plan
                    ai_side = plan.get("side")
                else:
                    logging.info("Scalp AI returned no tradable side → skip entry")
                    if not force_entry_after_ai:
                        return False

            if ai_side in ("long", "short"):
                tp_pips = float(
                    plan.get("tp_pips", env_loader.get_env("SCALP_TP_PIPS", "2"))
                )
                sl_pips = float(
                    plan.get("sl_pips", env_loader.get_env("SCALP_SL_PIPS", "1"))
                )
                wait_pips = float(plan.get("wait_pips", 0))
                side = ai_side
                mode = "market"
                limit_price = None
                price_ref = bid if side == "long" else ask
                if wait_pips > 0 and price_ref is not None:
                    limit_price = pullback_limit(side, price_ref, wait_pips)
                    mode = "limit"
            else:
                logging.info("Scalp AI returned no tradable side → skip entry")
                if not force_entry_after_ai:
                    return False
            price = bid if side == "long" else ask
            tf = env_loader.get_env("SCALP_COND_TF", "M1").upper()
            extra_tp, extra_sl = _calc_scalp_tp_sl(
                indicators,
                indicators_multi,
                tf,
                price,
                side,
                pip_size,
            )
            if tp_pips is None:
                tp_pips = extra_tp
            if sl_pips is None:
                sl_pips = extra_sl
            if tp_pips is None:
                tp_pips = float(env_loader.get_env("SCALP_TP_PIPS", "2"))
            if sl_pips is None:
                sl_pips = float(env_loader.get_env("SCALP_SL_PIPS", "1"))

            if trade_mode == "scalp_reversion":
                rev_tp, rev_sl = _calc_reversion_tp_sl(indicators, pip_size)
                if rev_tp is not None:
                    tp_pips = rev_tp
                if rev_sl is not None:
                    sl_pips = rev_sl

            # --- Volatility / spread filters for scalping ------------------
            try:
                cool_bw = float(env_loader.get_env("COOL_BBWIDTH_PCT", "0"))
                cool_atr = float(env_loader.get_env("COOL_ATR_PCT", "0"))
                bb_upper = indicators.get("bb_upper")
                bb_lower = indicators.get("bb_lower")
                atr_series = indicators.get("atr")
                if (
                    (cool_bw > 0 or cool_atr > 0)
                    and bb_upper is not None
                    and bb_lower is not None
                    and atr_series is not None
                    and len(bb_upper)
                    and len(bb_lower)
                    and len(atr_series)
                ):
                    u = (
                        float(bb_upper.iloc[-1])
                        if hasattr(bb_upper, "iloc")
                        else float(bb_upper[-1])
                    )
                    l = (
                        float(bb_lower.iloc[-1])
                        if hasattr(bb_lower, "iloc")
                        else float(bb_lower[-1])
                    )
                    atr_val = (
                        float(atr_series.iloc[-1])
                        if hasattr(atr_series, "iloc")
                        else float(atr_series[-1])
                    )
                    bw_ratio = (u - l) / atr_val if atr_val else float("inf")
                    if (cool_bw > 0 and bw_ratio < cool_bw) or (
                        cool_atr > 0 and atr_val < cool_atr
                    ):
                        logging.info(
                            "Volatility too low (bw_ratio %.2f / atr %.2f) \u2192 skip scalp entry",
                            bw_ratio,
                            atr_val,
                        )
                        if not force_entry_after_ai:
                            return False
            except Exception as exc:
                logging.debug(f"[process_entry] scalp vol filter failed: {exc}")

            # スプレッドに基づくエントリーブロックは行わない

            params = {
                "instrument": (
                    market_data["prices"][0]["instrument"]
                    if isinstance(market_data, dict)
                    else env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
                ),
                "tp_pips": tp_pips,
                "sl_pips": sl_pips,
                "mode": mode,
                "limit_price": limit_price,
                "ai_response": "scalp",
                "market_cond": market_cond,
            }
            with_oco = True
            try:
                if tp_only_condition(sl_pips, noise_pips):
                    with_oco = False
            except Exception:
                pass
            if trade_mode == "scalp_reversion":
                params["time_limit_sec"] = float(
                    env_loader.get_env("SCALP_REV_TIME_LIMIT_SEC", "120")
                )
            risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
            pip_val = float(env_loader.get_env("PIP_VALUE_JPY", "100"))
            lot = calc_lot_size(
                float(env_loader.get_env("ACCOUNT_BALANCE", "10000")),
                risk_pct,
                sl_pips,
                pip_val,
                risk_engine=risk_engine,
            )
            result = order_manager.enter_trade(
                side=side,
                lot_size=lot if lot > 0 else 0.0,
                market_data=market_data,
                strategy_params=params,
                force_limit_only=False,
                with_oco=with_oco,
            )
            return bool(result)
        except Exception as exc:
            logging.debug(f"[process_entry] scalp mode failed: {exc}")

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

    indicators_multi = (
        {"M5": indicators}
        if indicators_multi is None
        else {k.upper(): v for k, v in indicators_multi.items()}
    )
    plan = oa.get_trade_plan(
        market_data,
        indicators_multi,
        candles_dict,
        patterns=patterns,
        detected_patterns=detected,
        allow_delayed_entry=allow_delayed_entry,
        filter_ctx=strategy_params.get("filter_ctx") if isinstance(strategy_params, dict) else None,
    )

    # AI_RETRY_ON_NO 機能は廃止されたため、ここでの再試行は行わない

    # Raw JSON for audit log
    ai_raw = json.dumps(plan, ensure_ascii=False)
    logging.info(f"AI trade plan raw: {ai_raw}")
    entry_type = plan.get("entry_type")
    if entry_type:
        logging.info(f"Entry type from AI: {entry_type}")
        if entry_type != "pullback" and trade_mode == "trend_follow":
            trade_mode = "scalp_momentum"
            strong_trend_mode = False


    llm_regime = (plan.get("regime") or {}).get("market_condition")
    local_mode, _score, _ = decide_trade_mode_detail(indicators)
    local_regime = "trend" if local_mode in ("trend_follow", "strong_trend") else "range"
    momentum_score = None
    try:
        mom = indicators.get("momentum", {})
        if isinstance(mom, dict):
            momentum_score = float(mom.get("score"))
    except Exception:
        momentum_score = None
    if (
        momentum_score is not None
        and momentum_score >= 0.5
        and llm_regime == "range"
        and local_regime == "trend"
    ):
        logging.info(
            "Regime conflict resolved in favor of local trend (momentum.score=%.2f)",
            momentum_score,
        )
        plan.setdefault("regime", {})["market_condition"] = local_regime
        if market_cond is not None:
            market_cond["market_condition"] = local_regime

    entry_info = plan.get("entry", {})
    risk_info = plan.get("risk", {})

    side = entry_info.get("side", "no").lower()
    mode = entry_info.get("mode", "market")
    limit_price = entry_info.get("limit_price")
    if strong_trend_mode:
        mode = "market"
        limit_price = None
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
        fallback_force = (
            env_loader.get_env("FALLBACK_FORCE_ON_NO_SIDE", "false").lower()
            == "true"
        )
        if fallback_force:
            fallback_side = (market_cond or {}).get("trend_direction")
            if fallback_side in ("long", "short"):
                logging.info("Fallback forces side %s", fallback_side)
                side = fallback_side
                entry_info["side"] = side
                # このフラグが立つと後続のTF整合チェックをスキップする
                forced_entry = True
                risk_info = plan.setdefault("risk", {})
                if use_dynamic_risk:
                    dyn_tp, dyn_sl = calc_fallback_tp_sl(indicators, pip_size)
                    if dyn_sl is not None:
                        risk_info["sl_pips"] = dyn_sl
                    else:
                        risk_info.setdefault(
                            "sl_pips",
                            float(
                                env_loader.get_env(
                                    "FALLBACK_DEFAULT_SL_PIPS", "8"
                                )
                            ),
                        )
                    if dyn_tp is not None:
                        risk_info["tp_pips"] = dyn_tp
                    else:
                        risk_info.setdefault(
                            "tp_pips",
                            float(
                                env_loader.get_env(
                                    "FALLBACK_DEFAULT_TP_PIPS", "12"
                                )
                            ),
                        )
                else:
                    risk_info.setdefault(
                        "sl_pips",
                        float(env_loader.get_env("FALLBACK_DEFAULT_SL_PIPS", "8")),
                    )
                    risk_info.setdefault(
                        "tp_pips",
                        float(env_loader.get_env("FALLBACK_DEFAULT_TP_PIPS", "12")),
                    )

    if side not in ("long", "short"):
        if force_entry_after_ai:
            side = (market_cond or {}).get("trend_direction") or "long"
            entry_info["side"] = side
        else:
            logger.debug("reject: reason=AI_DECISION side=%s", side)
            logger.debug("reject: reason=%s", plan.get("reason"))
            logging.info("AI says no trade entry → early exit")
            return False

    if return_side:
        return side if side in ("long", "short") else None

    # スプレッドによるエントリー停止は無効化

    if PEAK_ENTRY_ENABLED:
        try:
            from backend.strategy.signal_filter import detect_peak_reversal

            m5 = candles_dict.get("M5", candles)
            if detect_peak_reversal(m5, side):
                side = "short" if side == "long" else "long"
                logging.info(f"Peak reversal detected → side flipped to {side}")
        except Exception as exc:
            logging.debug(f"[process_entry] peak reversal check failed: {exc}")

    # forced_entry が True の場合は上位足整合チェックをスキップ
    if tf_align and not forced_entry:
        try:
            from piphawk_ai.analysis.signal_filter import is_multi_tf_aligned

            align = is_multi_tf_aligned(indicators_multi, ai_side=side)
            if align and side != align:
                logging.info(f"AI side {side} realigned to {align} by multi‑TF check")
                side = align
            elif (
                align is None
                and env_loader.get_env(
                    "ALIGN_STRICT", env_loader.get_env("STRICT_TF_ALIGN", "false")
                ).lower()
                == "true"
            ):
                logging.info("Multi‑TF alignment missing → skip entry")
                if not force_entry_after_ai:
                    return False
        except Exception as exc:
            logging.debug(f"alignment adjust failed: {exc}")
            if (
                env_loader.get_env(
                    "ALIGN_STRICT", env_loader.get_env("STRICT_TF_ALIGN", "false")
                ).lower()
                == "true"
            ):
                logging.info("Alignment adjustment failed and strict mode → skip entry")
                if not force_entry_after_ai:
                    return False

    try:
        if getattr(oa, "is_entry_blocked_by_recent_candles", lambda *a, **k: False)(
            side, candles
        ):
            logging.info("Entry blocked by recent candle bias")
            if not force_entry_after_ai:
                return False
    except Exception as exc:
        logging.debug(f"[process_entry] bias check failed: {exc}")

    # --- extension block filter (disabled post-AI) ----------------
    # AI からの指示を優先するため、ここでのブロックは行わない

    # RSI ブロックは AI の判断を尊重して無効化

    # False break フィルタは無効化

    breakout_entry = False
    try:
        breakout_entry = should_enter_breakout(
            candles_dict.get("M5", candles), indicators
        )
    except Exception as exc:
        logging.debug(f"[process_entry] breakout check failed: {exc}")

    try:
        # --- static pullback filter disabled; rely on AI judgment ---
        pass
    except Exception as exc:
        logging.debug(f"[process_entry] trend-pullback check skipped: {exc}")

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
                if "mid" in c:
                    highs.append(float(c["mid"]["h"]))
                    lows.append(float(c["mid"]["l"]))
                else:
                    highs.append(float(c.get("h")))
                    lows.append(float(c.get("l")))
            recent_high = max(highs) if highs else 0.0
            recent_low = min(lows) if lows else 0.0
            pullback_needed = calculate_dynamic_pullback(
                {**indicators, "noise": noise_series}, recent_high, recent_low
            )
        except Exception:
            pass

        try:
            adx_series = indicators.get("adx")
            thresh = float(env_loader.get_env("BYPASS_PULLBACK_ADX_MIN", "0"))
            if strong_trend_mode:
                pullback_needed = None
            elif (
                thresh > 0
                and adx_series is not None
                and len(adx_series)
                and float(
                    adx_series.iloc[-1]
                    if hasattr(adx_series, "iloc")
                    else adx_series[-1]
                )
                >= thresh
            ):
                pullback_needed = None
        except Exception:
            pass

    if isinstance(market_data, dict):
        instrument = market_data["prices"][0]["instrument"]
        bid = float(market_data["prices"][0]["bids"][0]["price"])
        ask = float(market_data["prices"][0]["asks"][0]["price"])
    else:
        instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
        bid = ask = None

    # H1 レベルチェック無効化 (AI 指示を優先)

    if mode == "market" and not is_break:
        price_ref = bid if side == "long" else ask
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
            if (
                bb_upper is not None
                and bb_lower is not None
                and len(bb_upper)
                and len(bb_lower)
            ):
                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
                bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
                narrow_range = bw_pips < bw_thresh
        except Exception as exc:
            logging.debug(f"[process_entry] narrow-range detection failed: {exc}")

    # Range 市場での LIMIT 変換を無効化

    # スプレッドによる LIMIT 変換は実施しない

    if mode == "wait":
        logging.info("AI suggests WAIT – proceeding with entry.")

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
            mult_sl = float(
                env_loader.get_env(
                    "ATR_MULT_SL", env_loader.get_env("ATR_SL_MULTIPLIER", "2.0")
                )
            )
            fallback_sl = atr_pips * mult_sl
            mult_tp = float(
                env_loader.get_env(
                    "ATR_MULT_TP", env_loader.get_env("SHORT_TP_ATR_RATIO", "0.6")
                )
            )
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
        if bb_upper is not None and bb_lower is not None and price_ref is not None:
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

    if not use_dynamic_risk and forced_entry:
        fallback_tp = None
        fallback_sl = None
        dynamic_min_sl = 0.0

    if tp_pips is None:
        tp_pips = (
            fallback_tp
            if fallback_tp is not None
            else float(env_loader.get_env("INIT_TP_PIPS", "30"))
        )
    else:
        try:
            tp_pips = float(tp_pips)
        except Exception:
            tp_pips = float(env_loader.get_env("INIT_TP_PIPS", "30"))

    if sl_pips is None:
        sl_pips = (
            fallback_sl
            if fallback_sl is not None
            else float(env_loader.get_env("INIT_SL_PIPS", "20"))
        )
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
            tp_pips, sl_pips = adjust_sl_for_rr(tp_pips, sl_pips, min_rrr)
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

    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        spread = (ask - bid) / pip_size if bid is not None and ask is not None else 0.0
        slip = float(env_loader.get_env("ENTRY_SLIPPAGE_PIPS", "0"))
        min_rrr_cost = float(env_loader.get_env("MIN_RRR_AFTER_COST", "0"))
        if not validate_rrr_after_cost(tp_pips, sl_pips, spread + slip, min_rrr_cost):
            logging.info(
                f"RRR after cost {(tp_pips - (spread + slip)) / sl_pips if sl_pips else 0:.2f} < {min_rrr_cost} → skip entry"
            )
            if not force_entry_after_ai:
                return False
    except Exception as exc:
        logging.debug(f"[process_entry] rrr-after-cost check failed: {exc}")

    logging.info(f"AI Entry {side} – tp={tp_pips}  sl={sl_pips} (pips)")

    if mode == "limit":
        if limit_price is None:
            logging.warning("LIMIT mode but no limit_price → skip entry.")
            if not force_entry_after_ai:
                return False

        # Check if a similar pending order already exists
        open_orders = (
            order_manager.get_open_orders(instrument, side)
            if hasattr(order_manager, "get_open_orders")
            else []
        )
        if open_orders:
            logging.info("Existing pending order found – skip entry.")
            if not force_entry_after_ai:
                return False
        existing = get_pending_entry_order(instrument)
        if existing:
            logging.info(
                "Pending LIMIT order already exists – skip new limit placement."
            )
            if not force_entry_after_ai:
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
        risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
        if entry_type == "breakout":
            risk_pct *= 1.05
        elif entry_type == "reversal":
            risk_pct *= 0.95
        result = order_manager.enter_trade(
            side=side,
            lot_size=calc_lot_size(
                float(env_loader.get_env("ACCOUNT_BALANCE", "10000")),
                risk_pct,
                sl_pips,
                float(env_loader.get_env("PIP_VALUE_JPY", "100")),
                risk_engine=risk_engine,
            ),
            market_data=market_data,
            strategy_params=params_limit,
            force_limit_only=False,
            with_oco=not tp_only_condition(sl_pips, noise_pips),
        )
        if result:
            _pending_limits[entry_uuid] = {
                "instrument": instrument,
                "order_id": result.get("order_id"),
                "ts": int(datetime.now(timezone.utc).timestamp()),
                "limit_price": limit_price,
                "side": side,
                "retry_count": 0,
            }
        return bool(result)
    else:
        # --- MARKET order path ---
        if hasattr(order_manager, "get_open_orders") and order_manager.get_open_orders(
            instrument, side
        ):
            logging.info("Existing pending order found – skip market entry.")
            if not force_entry_after_ai:
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

    risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
    if entry_type == "breakout":
        risk_pct *= 1.05
    elif entry_type == "reversal":
        risk_pct *= 0.95
    trade_result = order_manager.enter_trade(
        side=side,
        lot_size=calc_lot_size(
            float(env_loader.get_env("ACCOUNT_BALANCE", "10000")),
            risk_pct,
            sl_pips,
            float(env_loader.get_env("PIP_VALUE_JPY", "100")),
            risk_engine=risk_engine,
        ),
        market_data=market_data,
        strategy_params=params,
        force_limit_only=False,
        with_oco=not tp_only_condition(sl_pips, noise_pips),
    )

    if trade_result and mode == "market":
        instrument = params["instrument"]
        risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
        if entry_type == "breakout":
            risk_pct *= 1.05
        elif entry_type == "reversal":
            risk_pct *= 0.95
        lot_size = calc_lot_size(
            float(env_loader.get_env("ACCOUNT_BALANCE", "10000")),
            risk_pct,
            sl_pips,
            float(env_loader.get_env("PIP_VALUE_JPY", "100")),
            risk_engine=risk_engine,
        )
        units = int(lot_size * 1000) if side == "long" else -int(lot_size * 1000)
        entry_price = float(market_data["prices"][0]["bids"][0]["price"])
        entry_time = datetime.now(timezone.utc).isoformat()
        rrr = None
        try:
            if tp_pips is not None and sl_pips not in (None, 0):
                rrr = float(tp_pips) / float(sl_pips)
        except Exception:
            rrr = None
        log_trade(
            instrument=instrument,
            entry_time=entry_time,
            entry_price=entry_price,
            units=units,
            ai_reason=ai_raw,
            ai_response=ai_raw,
            entry_regime=entry_type,
            regime=strategy_params.get("regime"),
            forced=forced_entry,
            tp_pips=tp_pips,
            sl_pips=sl_pips,
            rrr=rrr,
            is_manual=False,
        )

    return bool(trade_result)
