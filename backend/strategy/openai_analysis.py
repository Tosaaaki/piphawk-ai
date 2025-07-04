"""OpenAIモデルを用いたトレード分析ユーティリティ"""

import json
import logging

from piphawk_ai.ai.local_model import ask_model

# Backward compatibility for tests
ask_openai = ask_model
from piphawk_ai.ai.macro_analyzer import MacroAnalyzer

try:
    from backend.logs.log_manager import log_ai_decision, log_prompt_response
except Exception:  # テストでスタブが残っている場合のフォールバック
    def log_ai_decision(*_a, **_k) -> None:
        pass

    def log_prompt_response(*_a, **_k) -> None:
        pass
from backend.strategy.pattern_ai_detection import detect_chart_pattern
from backend.strategy.pattern_scanner import PATTERN_DIRECTION
from backend.utils import env_loader, parse_json_answer

try:
    from backend.indicators.ema import get_ema_gradient
except Exception:  # pragma: no cover - pandas may be unavailable
    def get_ema_gradient(*_a, **_k) -> str:
        return "flat"
from backend.analysis.atmosphere import evaluate as atmos_eval
from backend.indicators import compute_volume_sma, get_candle_features
from backend.indicators.adx import calculate_adx_slope
from backend.risk_manager import (
    calc_min_sl,
    get_recent_swing_diff,
    is_high_vol_session,
)
from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
from backend.strategy.openai_prompt import TREND_ADX_THRESH, build_trade_plan_prompt

USE_CANDLE_SUMMARY = env_loader.get_env("USE_CANDLE_SUMMARY", "false").lower() == "true"
import time
from datetime import datetime, timezone

from backend.config.defaults import MIN_ABS_SL_PIPS

# --- Added for AI-based exit decision ---
# Consolidated exit decision helpers live in exit_ai_decision
from backend.strategy.exit_ai_decision import AIDecision
from backend.strategy.exit_ai_decision import evaluate as evaluate_exit
from backend.strategy.validators import normalize_probs, risk_autofix


def _is_schema_valid(plan: dict) -> bool:
    """Return True if required probability fields sum to one."""
    try:
        conf = float(plan.get("entry_confidence", 0))
        if not 0.0 <= conf <= 1.0:
            return False
        probs = plan.get("probs")
        if not isinstance(probs, dict):
            return False
        vals = [float(probs.get(k, 0)) for k in ("long", "short", "no")]
        total = sum(vals)
        return abs(total - 1.0) <= 0.01
    except Exception:
        return False

macro_analyzer = MacroAnalyzer()

# ----------------------------------------------------------------------
# Config – driven by environment variables
# ----------------------------------------------------------------------
AI_COOLDOWN_SEC_FLAT: int = int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", 60))
AI_COOLDOWN_SEC_OPEN: int = int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", 60))
# Regime‑classification specific cooldown (defaults to flat cooldown)
AI_REGIME_COOLDOWN_SEC: int = int(
    env_loader.get_env("AI_REGIME_COOLDOWN_SEC", AI_COOLDOWN_SEC_FLAT)
)
AI_COOLDOWN_HIGH_VOL_MULT: float = float(
    env_loader.get_env("AI_COOLDOWN_HIGH_VOL_MULT", "0.5")
)

# --- Threshold for AI‑proposed TP probability ---
MIN_TP_PROB: float = float(env_loader.get_env("MIN_TP_PROB", "0.75"))
DYN_TP_PROB_FLOOR: float = float(env_loader.get_env("DYN_TP_PROB_FLOOR", "0.55"))
DYN_TP_PROB_CEIL: float = float(
    env_loader.get_env("DYN_TP_PROB_CEIL", str(MIN_TP_PROB))
)
TP_PROB_HOURS: int = int(env_loader.get_env("TP_PROB_HOURS", "24"))
PROB_MARGIN: float = float(env_loader.get_env("PROB_MARGIN", "0.1"))
MIN_EXPECTED_VALUE: float = float(
    env_loader.get_env("MIN_EXPECTED_VALUE", "0.0")
)
LIMIT_THRESHOLD_ATR_RATIO: float = float(env_loader.get_env("LIMIT_THRESHOLD_ATR_RATIO", "0.3"))
MAX_LIMIT_AGE_SEC: int = int(env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))
MIN_NET_TP_PIPS: float = float(env_loader.get_env("MIN_NET_TP_PIPS", "1"))
BE_TRIGGER_PIPS: int = int(env_loader.get_env("BE_TRIGGER_PIPS", 10))
BE_TRIGGER_R: float = float(env_loader.get_env("BE_TRIGGER_R", "0"))
AI_LIMIT_CONVERT_MODEL: str = env_loader.get_env("AI_LIMIT_CONVERT_MODEL", "gpt-4.1-nano")
MIN_RRR: float = float(env_loader.get_env("MIN_RRR", "0.8"))
# Apply entry-type boost only when enabled via environment
ENTRY_TYPE_BOOST: bool = env_loader.get_env("ENTRY_TYPE_BOOST", "false").lower() == "true"
# --- Composite score threshold ---
COMPOSITE_MIN: float = float(env_loader.get_env("COMPOSITE_MIN", "0.2"))
# --- Exit bias factor ---
EXIT_BIAS_FACTOR: float = float(env_loader.get_env("EXIT_BIAS_FACTOR", "1.0"))

# --- Volatility and ADX filters ---
COOL_BBWIDTH_PCT: float = float(env_loader.get_env("COOL_BBWIDTH_PCT", "0"))
COOL_ATR_PCT: float = float(env_loader.get_env("COOL_ATR_PCT", "0"))
# ADXノートレード域のデフォルト値を15-18に緩和
ADX_NO_TRADE_MIN: float = float(env_loader.get_env("ADX_NO_TRADE_MIN", "15"))
ADX_NO_TRADE_MAX: float = float(env_loader.get_env("ADX_NO_TRADE_MAX", "18"))
ADX_SLOPE_LOOKBACK: int = int(env_loader.get_env("ADX_SLOPE_LOOKBACK", "3"))
ALLOW_NO_PULLBACK_WHEN_ADX: float = float(
    env_loader.get_env("ALLOW_NO_PULLBACK_WHEN_ADX", "0")
)
BYPASS_PULLBACK_ADX_MIN: float = float(
    env_loader.get_env("BYPASS_PULLBACK_ADX_MIN", "0")
)
ENABLE_RANGE_ENTRY: bool = (
    env_loader.get_env("ENABLE_RANGE_ENTRY", "false").lower() == "true"
)
VOL_SPIKE_ADX_MULT: float = float(env_loader.get_env("VOL_SPIKE_ADX_MULT", "1.5"))
VOL_SPIKE_ATR_MULT: float = float(env_loader.get_env("VOL_SPIKE_ATR_MULT", "1.5"))
ADX_TREND_ON: int = 25
ADX_TREND_OFF: int = 18
USE_LOCAL_PATTERN: bool = (
    env_loader.get_env("USE_LOCAL_PATTERN", "false").lower() == "true"
)
# Local/AI blending threshold for market regime decision
LOCAL_WEIGHT_THRESHOLD: float = float(
    env_loader.get_env("LOCAL_WEIGHT_THRESHOLD", "0.6")
)
# Disable regime conflict resolution when true
IGNORE_REGIME_CONFLICT: bool = (
    env_loader.get_env("IGNORE_REGIME_CONFLICT", "false").lower() == "true"
)

# --- Consistency weight configuration ---------------------------
_DEFAULT_CONSISTENCY_WEIGHTS = {"ema": 0.4, "adx": 0.3, "rsi": 0.3}
_consistency_weights = _DEFAULT_CONSISTENCY_WEIGHTS.copy()
_cw_env = env_loader.get_env("CONSISTENCY_WEIGHTS")
if _cw_env:
    try:
        parsed: dict[str, float] = {}
        for part in _cw_env.split(","):
            key, val = part.split(":")
            parsed[key.strip()] = float(val)
        total_w = sum(parsed.values())
        if total_w != 0:
            if abs(total_w - 1.0) > 0.1:
                logging.getLogger(__name__).warning(
                    "CONSISTENCY_WEIGHTS sum %.2f, normalizing", total_w
                )
            parsed = {k: v / total_w for k, v in parsed.items()}
        _consistency_weights.update(parsed)
    except Exception as exc:  # pragma: no cover - just log
        logging.getLogger(__name__).warning(
            "Invalid CONSISTENCY_WEIGHTS: %s; using defaults", exc
        )
        _consistency_weights = _DEFAULT_CONSISTENCY_WEIGHTS.copy()

# --- Dynamic weight multipliers ------------------------------------
HIGH_VOL_WEIGHT_MULT: float = float(
    env_loader.get_env("HIGH_VOL_WEIGHT_MULT", "1.2")
)
LOW_VOL_WEIGHT_MULT: float = float(
    env_loader.get_env("LOW_VOL_WEIGHT_MULT", "1.0")
)


def _get_dynamic_weight(key: str) -> float:
    """Return indicator weight adjusted by session volatility."""
    base = _consistency_weights.get(key, 0.0)
    factor = HIGH_VOL_WEIGHT_MULT if is_high_vol_session() else LOW_VOL_WEIGHT_MULT
    return base * factor

# Global variables to store last AI call timestamps
_last_exit_ai_call_time = 0.0
# Regime‑AI cache
_last_regime_ai_call_time = 0.0

_cached_regime_result: dict | None = None

# --- Market trend state for hysteresis control ---------------------
_trend_active: bool = False

# DI crossの最後の検知時刻（バーインデックス）を保持する
_last_di_cross_ts: int | None = None



def _series_tail_list(series, n: int = 20) -> list:
    """Return the last ``n`` values from a pandas Series or list."""
    if series is None:
        return []
    try:
        if hasattr(series, "iloc"):
            return series.iloc[-n:].tolist()
        if isinstance(series, (list, tuple)):
            return list(series)[-n:]
        return [series]
    except Exception:
        return []

def get_ai_cooldown_sec(current_position: dict | None) -> int:
    """Return AI cooldown seconds adjusted for volatility."""
    base = AI_COOLDOWN_SEC_OPEN
    if current_position:
        try:
            units_val = float(current_position.get("units", 0))
        except (TypeError, ValueError):
            units_val = 0.0
        if units_val == 0:
            try:
                units_val = float(current_position.get("long", {}).get("units", 0))
            except (TypeError, ValueError):
                units_val = 0.0
            if units_val == 0:
                try:
                    units_val = float(current_position.get("short", {}).get("units", 0))
                except (TypeError, ValueError):
                    units_val = 0.0
        if abs(units_val) > 0:
            base = AI_COOLDOWN_SEC_FLAT
    if is_high_vol_session():
        base = max(1, int(base * AI_COOLDOWN_HIGH_VOL_MULT))
    return base

logger = logging.getLogger(__name__)

logger.info("OpenAI Analysis started")


# ----------------------------------------------------------------------
# Consistency scoring
# ----------------------------------------------------------------------
def calc_consistency(
    local: str | None,
    ai: str | None,
    ema_ok: float = 0.0,
    adx_ok: float = 0.0,
    rsi_cross_ok: float = 0.0,
) -> float:
    """Return a blended consistency score between local indicators and AI."""

    if not local or not ai:
        ai_score = 0.5
    else:
        # When local and AI disagree, use a neutral score instead of zero
        ai_score = 1.0 if local == ai else 0.5

    local_score = (
        ema_ok * _get_dynamic_weight("ema")
        + adx_ok * _get_dynamic_weight("adx")
        + rsi_cross_ok * _get_dynamic_weight("rsi")
    )

    alpha = LOCAL_WEIGHT_THRESHOLD * local_score + (1 - LOCAL_WEIGHT_THRESHOLD) * ai_score
    return alpha


def _apply_entry_type_boost(score: float, entry_type: str) -> float:
    """Return score adjusted by entry type and clipped."""
    if not ENTRY_TYPE_BOOST:
        return score
    boost = 0.0
    if entry_type == "breakout":
        boost = 0.05
    elif entry_type == "reversal":
        boost = -0.05
    new_score = score + boost
    new_score = max(-0.4, min(new_score, 0.6))
    logging.getLogger(__name__).info(
        "entry_type %s -> score %.2f", entry_type, new_score
    )
    return new_score


def _classify_entry_type(market_cond: dict | None, pullback_done: bool) -> str:
    """Classify entry type from market condition and pullback state."""
    if market_cond and market_cond.get("market_condition") == "break":
        return "breakout"
    if pullback_done:
        return "pullback"
    return "reversal"



# ----------------------------------------------------------------------
# Market‑regime classification helper (OpenAI direct, enhanced English prompt)
# ----------------------------------------------------------------------
from backend.strategy.range_break import (
    classify_breakout,
    detect_atr_breakout,
    detect_range_break,
)


def get_market_condition(context: dict, higher_tf: dict | None = None) -> dict:
    """
    Determine whether the market is in a 'trend' or 'range' state.
        The function combines a heuristic, indicator‑based assessment
    (ADX + EMA slope) with an LLM assessment.  
    If both disagree, the local heuristic wins.

    Returns
    -------
    dict
        {
            "market_condition": "trend" | "range" | "break",
            "range_break": "up" | "down" | None,
            "break_direction": "up" | "down" | None,
            "break_class": "trend" | "range" | None,
        }
    ``context`` may include ``indicators_h1`` and ``indicators_h4`` to
    improve the local regime decision.
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    global _last_di_cross_ts
    global _last_regime_ai_call_time, _cached_regime_result
    now = time.time()
    if (
        now - _last_regime_ai_call_time < AI_REGIME_COOLDOWN_SEC
        and _cached_regime_result is not None
    ):
        logger.info("Market condition cached (cooldown)")
        return _cached_regime_result
    indicators = context.get("indicators", {})
    ema_trend = None
    try:
        fast_vals = indicators.get("ema_fast")
        if fast_vals is not None:
            ema_trend = get_ema_gradient(fast_vals)
    except Exception:
        ema_trend = None
    context["ema_trend"] = ema_trend

    # ------------------------------------------------------------------
    # 1) Local regime assessment (ADX + EMA slope consistency)
    # ------------------------------------------------------------------
    adx_vals = indicators.get("adx")
    ema_vals = indicators.get("ema_slope")
    ind_m1 = context.get("indicators_m1") or {}
    ind_h1 = context.get("indicators_h1") or {}
    ind_h4 = context.get("indicators_h4") or {}

    # --- Bollinger band width for dynamic ADX threshold -----------------
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    bw_pips = None
    try:
        if bb_upper is not None and bb_lower is not None:
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            bb_u = float(bb_upper.iloc[-1]) if hasattr(bb_upper, "iloc") else float(bb_upper[-1])
            bb_l = float(bb_lower.iloc[-1]) if hasattr(bb_lower, "iloc") else float(bb_lower[-1])
            bw_pips = (bb_u - bb_l) / pip_size
    except Exception:
        bw_pips = None
    bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
    adx_base = float(env_loader.get_env("ADX_RANGE_THRESHOLD", "25"))
    coeff = float(env_loader.get_env("ADX_DYNAMIC_COEFF", "0"))
    width_ratio = (
        (bw_pips - bw_thresh) / bw_thresh
        if bw_pips is not None and bw_thresh != 0
        else 0.0
    )
    adx_dynamic_thresh = adx_base * (1 + coeff * width_ratio)

    # DI cross detection for trend reversal
    plus_di = indicators.get("plus_di")
    minus_di = indicators.get("minus_di")
    di_cross = False
    current_idx = None
    try:
        def _tail2(series):
            if series is None:
                return []
            if hasattr(series, "iloc"):
                return [float(v) for v in series.iloc[-2:]]
            if isinstance(series, (list, tuple)):
                return [float(v) for v in series[-2:]]
            return [float(series)]

        p_vals = _tail2(plus_di)
        m_vals = _tail2(minus_di)
        if plus_di is not None:
            try:
                current_idx = len(plus_di)
            except Exception:
                current_idx = 1
        else:
            current_idx = None
        if len(p_vals) >= 2 and len(m_vals) >= 2:
            p_prev, p_cur = p_vals[-2], p_vals[-1]
            m_prev, m_cur = m_vals[-2], m_vals[-1]
            di_cross = (p_prev > m_prev and p_cur < m_cur) or (p_prev < m_prev and p_cur > m_cur)
    except Exception:
        di_cross = False
        current_idx = None

    if di_cross and current_idx is not None:
        _last_di_cross_ts = current_idx

    cross_age = None
    if _last_di_cross_ts is not None and current_idx is not None:
        cross_age = current_idx - _last_di_cross_ts

    if cross_age is not None and cross_age <= 5:
        logger.info("di_cross_lock: %s bars since DI cross", cross_age)
        return {
            "market_condition": "range",
            "range_break": None,
            "break_direction": None,
            "break_class": None,
        }

    # --- Cache check: reuse recent AI result if cooldown active ---------
    now = time.time()
    if (
        _cached_regime_result is not None
        and now - _last_regime_ai_call_time < AI_REGIME_COOLDOWN_SEC
    ):
        logger.info("Regime decision skipped (cooldown)")
        return _cached_regime_result

    def _extract_latest(series, n: int = 3):
        if series is None:
            return []
        try:
            if hasattr(series, "iloc"):
                return [float(x) for x in series.iloc[-n:]]
            if isinstance(series, (list, tuple)):
                return [float(x) for x in series[-n:]]
            return [float(series)]
        except Exception:
            return []

    # latest ADX value
    adx_latest = None
    if adx_vals is not None:
        try:
            if hasattr(adx_vals, "iloc"):
                adx_latest = float(adx_vals.iloc[-1])
            elif isinstance(adx_vals, (list, tuple)):
                adx_latest = float(adx_vals[-1]) if adx_vals else None
            else:
                adx_latest = float(adx_vals)
        except Exception:
            adx_latest = None

    trend_dir = None
    try:
        if (
            adx_latest is not None
            and adx_latest > TREND_ADX_THRESH
            and plus_di is not None
            and minus_di is not None
        ):
            if hasattr(plus_di, "iloc"):
                di_plus_val = float(plus_di.iloc[-1])
                di_minus_val = float(minus_di.iloc[-1])
            elif isinstance(plus_di, (list, tuple)):
                di_plus_val = float(plus_di[-1])
                di_minus_val = float(minus_di[-1])
            else:
                di_plus_val = float(plus_di)
                di_minus_val = float(minus_di)
            if di_plus_val > di_minus_val:
                trend_dir = "long"
            elif di_minus_val > di_plus_val:
                trend_dir = "short"
    except Exception:
        trend_dir = None

    # --- Hysteresis control for trend/range state -------------------
    global _trend_active
    if adx_latest is not None:
        prev_state = _trend_active
        if _trend_active:
            if adx_latest <= ADX_TREND_OFF:
                _trend_active = False
        else:
            if adx_latest >= ADX_TREND_ON:
                _trend_active = True
        if prev_state != _trend_active:
            logger.info(
                "Regime change: %s -> %s (ADX %.2f)",
                "trend" if prev_state else "range",
                "trend" if _trend_active else "range",
                adx_latest,
            )

    adx_slope = None
    if adx_vals is not None:
        try:
            adx_slope = calculate_adx_slope(adx_vals, lookback=ADX_SLOPE_LOOKBACK)
        except Exception:
            adx_slope = None

    # EMAの傾きが無い場合はema_fastから代用の傾きを算出
    ema_series = _extract_latest(ema_vals, n=5)
    if not ema_series:
        fast_vals = indicators.get("ema_fast")
        fast_series = _extract_latest(fast_vals, n=5)
        if len(fast_series) >= 2:
            ema_series = [fast_series[i] - fast_series[i - 1] for i in range(1, len(fast_series))]
    ema_sign_consistent = False
    if len(ema_series) >= 2:
        pos = [v > 0 for v in ema_series]
        neg = [v < 0 for v in ema_series]
        ema_sign_consistent = all(pos) or all(neg)
    if ema_trend == "flat":
        ema_sign_consistent = False
    ema_ok = 1.0 if ema_sign_consistent and ema_trend != "flat" else 0.0

    adx_ok = 1.0 if adx_latest is not None and adx_latest >= TREND_ADX_THRESH else 0.0
    if adx_ok > 0 and adx_slope is not None and adx_slope < 0:
        adx_ok *= 0.5

    rsi_cross_ok = 0.0
    rsi_m1 = ind_m1.get("rsi")
    if rsi_m1 is not None:
        try:
            from backend.strategy.signal_filter import _rsi_cross_up_or_down
            if _rsi_cross_up_or_down(rsi_m1):
                rsi_cross_ok = 1.0
        except Exception:
            rsi_cross_ok = 0.0

    # Bollinger Band width check (narrow band implies range)
    narrow_bw = False
    bw_pips = None
    try:
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
            bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
            narrow_bw = bw_pips <= bw_thresh
    except Exception:
        narrow_bw = False

    local_regime = None
    if di_cross:
        local_regime = "range"
    elif adx_latest is not None and ema_sign_consistent:
        local_regime = "trend" if adx_latest >= adx_dynamic_thresh else "range"
    elif adx_latest is not None:
        local_regime = "range"
    else:
        local_regime = "trend" if _trend_active else "range"

    if _trend_active and local_regime == "range":
        local_regime = "trend"

    # --- check M1 indicators before higher timeframes -----------------
    if local_regime is None:
        m1_adx = ind_m1.get("adx")
        m1_ema = ind_m1.get("ema_slope")
        m1_adx_val = None
        if m1_adx is not None:
            try:
                if hasattr(m1_adx, "iloc"):
                    m1_adx_val = float(m1_adx.iloc[-1])
                elif isinstance(m1_adx, (list, tuple)):
                    m1_adx_val = float(m1_adx[-1]) if m1_adx else None
                else:
                    m1_adx_val = float(m1_adx)
            except Exception:
                m1_adx_val = None
        m1_ema_series = _extract_latest(m1_ema, n=3)
        m1_ema_ok = len(m1_ema_series) >= 2 and (
            all(v > 0 for v in m1_ema_series) or all(v < 0 for v in m1_ema_series)
        )
        if m1_adx_val is not None and m1_adx_val >= adx_dynamic_thresh and m1_ema_ok:
            local_regime = "trend"

    def _is_trend(ind: dict) -> bool | None:
        adx = ind.get("adx")
        ema = ind.get("ema_slope")
        if adx is None or ema is None:
            return None
        try:
            if hasattr(adx, "iloc"):
                adx_val = float(adx.iloc[-1])
            elif isinstance(adx, (list, tuple)):
                adx_val = float(adx[-1]) if adx else None
            else:
                adx_val = float(adx)
        except Exception:
            adx_val = None
        ema_series = _extract_latest(ema)
        ema_ok_local = len(ema_series) >= 3 and (
            all(v > 0 for v in ema_series) or all(v < 0 for v in ema_series)
        )
        try:
            ema_dir = get_ema_gradient(ind.get("ema_fast"))
            if ema_dir == "flat":
                ema_ok_local = False
        except Exception:
            pass
        if adx_val is None or not ema_ok_local:
            return None
        return adx_val >= adx_dynamic_thresh

    if local_regime is None:
        for ind in (ind_h4, ind_h1):
            if _is_trend(ind):
                local_regime = "trend"
                break

    if narrow_bw:
        local_regime = "range"

    # ------------------------------------------------------------------
    # 2) LLM assessment (JSON‑only response)
    # ------------------------------------------------------------------
    prompt = (
        "Based on the current market data and indicators provided below, "
        "determine whether the market is in a 'trend' or 'range' state.\n\n"
        "### Evaluation Criteria:\n"
        "- Short‑term price action: consecutive candles strongly moving in one "
        "  direction suggest a trend.\n"
        "- EMA slope and price relationship: prices consistently above or below "
        "  EMA indicate a trending market.\n"
        "- ADX value: a value above 25 typically indicates a trending market.\n"
        "- RSI extremes: extremely low or high RSI values can suggest range‑bound "
        "  conditions but must be evaluated alongside short‑term price movements.\n\n"
        "If RSI stays consistently near or below 30 for multiple candles, this "
        "indicates a strong bearish trend rather than oversold range conditions.\n"
        "Conversely, if RSI stays consistently near or above 70 for multiple "
        "candles, this indicates a strong bullish trend rather than overbought "
        "range conditions.\n"
        + (
            f"Bollinger band width has contracted to {bw_pips:.1f} pips; range may be forming.\n"
            if narrow_bw and bw_pips is not None
            else ""
        )
        + f"### Market Data and Indicators:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        "Respond with JSON: {\"market_condition\":\"trend|range\"}"
    )

    try:
        # Request JSON‑object response if the client supports it
        llm_raw = ask_openai(
            prompt,
            response_format={"type": "json_object"},
        )
        if isinstance(llm_raw, dict):  # already parsed
            llm_regime = llm_raw.get("market_condition", "range")
            raw_text = json.dumps(llm_raw, ensure_ascii=False)
        else:
            llm_regime = json.loads(llm_raw).get("market_condition", "range")
            raw_text = str(llm_raw)
        log_prompt_response(
            "REGIME",
            env_loader.get_env("DEFAULT_PAIR", "USD_JPY"),
            prompt,
            raw_text,
        )
    except Exception as exc:
        logger.error("get_market_condition ‑ LLM failure: %s", exc)
        llm_regime = "range"

    # ------------------------------------------------------------------
    # 3) Reconcile local vs LLM assessments using consistency score
    # ------------------------------------------------------------------
    alpha = calc_consistency(
        local_regime, llm_regime, ema_ok=ema_ok, adx_ok=adx_ok, rsi_cross_ok=rsi_cross_ok
    )
    local_score = 1.0 if local_regime == "trend" else 0.0
    ai_score = 1.0 if llm_regime == "trend" else 0.0
    blended = alpha * local_score + (1 - alpha) * ai_score
    final_regime = "trend" if blended >= 0.5 else "range"

    if (
        local_regime
        and llm_regime != local_regime
        and not IGNORE_REGIME_CONFLICT
    ):
        if alpha >= LOCAL_WEIGHT_THRESHOLD:
            final_regime = local_regime
        elif (1 - alpha) >= LOCAL_WEIGHT_THRESHOLD:
            final_regime = llm_regime

    if (
        local_regime
        and llm_regime != local_regime
        and not IGNORE_REGIME_CONFLICT
    ):
        logger.warning(
            "LLM regime '%s' conflicts with local regime '%s'; alpha=%.2f -> %s",
            llm_regime,
            local_regime,
            alpha,
            final_regime,
        )

    # ------------------------------------------------------------------
    # 4) Optional range‑break analysis
    # ------------------------------------------------------------------
    range_break = None
    break_class = None
    candles = context.get("candles_m5")
    if candles:
        pivot = None
        if higher_tf:
            pivot = (
                higher_tf.get("pivot_h1")
                or higher_tf.get("pivot_h4")
                or higher_tf.get("pivot_d")
            )
        br = detect_range_break(candles, pivot=pivot)
        if br["break"]:
            range_break = br["direction"]
            break_class = classify_breakout(indicators)
            final_regime = "break"

        # --- ATR ブレイク判定 ----------------------------------------
        atr_series = indicators.get("atr")
        atr_break = (
            detect_atr_breakout(candles, atr_series) if atr_series is not None else None
        )
        if atr_break:
            final_regime = "break"
            range_break = atr_break

    result = {
        "market_condition": final_regime,
        "range_break": range_break,
        "break_direction": range_break,
        "break_class": break_class,
        "trend_direction": trend_dir,
    }
    _cached_regime_result = result
    _last_regime_ai_call_time = now
    return result



# ----------------------------------------------------------------------
# Entry decision
# ----------------------------------------------------------------------
def get_entry_decision(market_data, strategy_params, indicators=None, candles_dict=None, market_cond=None, higher_tf=None, higher_tf_direction=None):
    plan = get_trade_plan(market_data, indicators or {}, candles_dict or {}, strategy_params, higher_tf_direction=higher_tf_direction)
    return plan.get("entry", {"side": "no"})



# ----------------------------------------------------------------------
# Exit decision
# ----------------------------------------------------------------------
def get_exit_decision(
    market_data,
    current_position,
    indicators=None,
    entry_regime=None,
    market_cond=None,
    higher_tf=None,
    indicators_m1: dict | None = None,
    candles: list | None = None,
    patterns: list[str] | None = None,
    detected_patterns: dict[str, str | None] | None = None,
    instrument: str | None = None,
):
    """
    Ask the LLM whether we should exit an existing position.
    Returns a JSON-formatted string like:
        {"action":"EXIT","reason":"Price above BB upper"}

    higher_tf (dict|None): higher‑timeframe reference levels
    """
    global _last_exit_ai_call_time
    now = time.time()
    cooldown = get_ai_cooldown_sec(current_position)
    if now - _last_exit_ai_call_time < cooldown:
        logger.info("Exit decision skipped (cooldown)")
        return {"action": "HOLD", "reason": "Cooldown active"}

    if instrument is None:
        instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")

    if indicators is None:
        indicators = {}

    # Ensure ADX is present for regime‑shift reasoning
    if "adx" not in indicators and "adx" in market_data:
        indicators["adx"] = market_data.get("adx")

    higher_tf_json = json.dumps(higher_tf) if higher_tf else "{}"
    market_cond_json = json.dumps(market_cond) if market_cond else "{}"
    entry_regime_json = json.dumps(entry_regime) if entry_regime else "{}"

    units_val = float(current_position.get("units", 0))
    side = "SHORT" if units_val < 0 else "LONG"

    pips_from_entry = None
    unreal_pnl = 0
    # --- 現在値とエントリ価格からサイド別の差分を算出する ---
    try:
        bid = float(market_data.get("bid")) if isinstance(market_data, dict) else None
        ask = float(market_data.get("ask")) if isinstance(market_data, dict) else None
        avg_price = float(current_position.get("average_price"))
        if side == "LONG" and bid is not None:
            pips_from_entry = (bid - avg_price) * 100
            unreal_pnl = (bid - avg_price) * units_val
        elif side == "SHORT" and ask is not None:
            pips_from_entry = (avg_price - ask) * 100
            unreal_pnl = (avg_price - ask) * -units_val
        else:
            pips_from_entry = 0
            unreal_pnl = 0
    except (ValueError, TypeError):
        # ここでは値を設定せず、後続のフォールバックに任せる
        pips_from_entry = None
        unreal_pnl = 0

    secs_since_entry = market_data.get("secs_since_entry")

    if secs_since_entry is None:
        try:
            entry_time_str = current_position.get("entry_time") or current_position.get("openTime")
            if entry_time_str:
                entry_dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                secs_since_entry = (datetime.now(timezone.utc) - entry_dt).total_seconds()
        except Exception:
            secs_since_entry = None

    # --------------------------------------------------------------
    # Break‑even trigger (fallback)
    # --------------------------------------------------------------
    if pips_from_entry is None:
        try:
            bid = float(market_data.get("bid")) if isinstance(market_data, dict) else None
            ask = float(market_data.get("ask")) if isinstance(market_data, dict) else None
            avg_price = float(current_position.get("average_price"))
            if side == "LONG" and bid:
                pips_from_entry = (bid - avg_price) * 100
            elif side == "SHORT" and ask:
                pips_from_entry = (avg_price - ask) * 100
            else:
                pips_from_entry = 0
        except (ValueError, TypeError):
            pips_from_entry = 0

    BE_ATR_TRIGGER_MULT = float(env_loader.get_env("BE_ATR_TRIGGER_MULT", "0"))
    if BE_ATR_TRIGGER_MULT > 0:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        atr_val = indicators.get("atr")
        if hasattr(atr_val, "iloc"):
            atr_val = atr_val.iloc[-1]
        elif isinstance(atr_val, list):
            atr_val = atr_val[-1]
        atr_pips = float(atr_val) / pip_size if atr_val is not None else 0.0
        be_trigger = max(BE_TRIGGER_PIPS, atr_pips * BE_ATR_TRIGGER_MULT)
    else:
        be_trigger = BE_TRIGGER_PIPS
    if BE_TRIGGER_R > 0:
        sl_val = None
        if entry_regime and isinstance(entry_regime, dict):
            sl_val = entry_regime.get("sl")
        if sl_val is None:
            sl_val = current_position.get("sl_pips")
        try:
            if sl_val is not None:
                sl_val = float(sl_val)
                be_trigger = max(be_trigger, sl_val * BE_TRIGGER_R)
        except Exception:
            pass

    breakeven_reached = pips_from_entry >= be_trigger

    # Ensure all indicator values are JSON serializable (e.g., pandas Series to list)
    indicators_serializable = {
        key: value.tolist() if hasattr(value, "tolist") else value
        for key, value in indicators.items()
    }
    indicators_m1_serializable = (
        {
            key: value.tolist() if hasattr(value, "tolist") else value
            for key, value in indicators_m1.items()
        }
        if indicators_m1
        else {}
    )

    pattern_name = None
    if patterns:
        try:
            if USE_LOCAL_PATTERN:
                from backend.strategy.pattern_scanner import scan_all
                pattern_name = scan_all(candles or [])
            else:
                pattern_res = detect_chart_pattern(candles or [], patterns)
                pattern_name = pattern_res.get("pattern")
        except Exception:
            pattern_name = None

    pattern_line = None
    if detected_patterns:
        try:
            pattern_line = ", ".join(
                f"{tf}:{p}" for tf, p in detected_patterns.items() if p
            ) or None
        except Exception:
            pattern_line = str(detected_patterns)
    elif pattern_name:
        pattern_line = pattern_name
            
    atmosphere_score, atmosphere_bias = atmos_eval(
        {
            "market_data": market_data,
            "indicators": indicators,
            "indicators_m1": indicators_m1,
            "position": current_position,
            "entry_regime": entry_regime,
            "market_cond": market_cond,
            "candles": candles,
            "higher_tf": higher_tf,
        }
    )
    if atmosphere_bias > 0.2:
        bias_label = "Up"
    elif atmosphere_bias < -0.2:
        bias_label = "Down"
    else:
        bias_label = "Neutral"

    prompt = (
        "You are an expert FX trader AI. Your job is to decide, with clear and concise reasoning, whether to HOLD or EXIT an open position based on the latest market context and indicators.\n"
        f"EXIT_BIAS_FACTOR={EXIT_BIAS_FACTOR} (>1 favors EXIT, <1 favors HOLD).\n\n"
        f"### ATMOSPHERE SCORE\n{atmosphere_score:.2f}\n"
        f"### ATMOSPHERE BIAS\n{bias_label}\n\n"
        f"### Position Details\n"
        f"- Side: {side}\n"
        f"- Time Since Entry: {secs_since_entry if secs_since_entry is not None else 'N/A'} sec\n"
        f"- Pips From Entry: {pips_from_entry:.1f}\n"
        f"- Unrealized P&L: {unreal_pnl}\n"
        f"- Entry Regime: {entry_regime_json}\n"
        f"- Market Condition: {market_cond_json}\n"
        f"- Higher Timeframe Levels: {higher_tf_json}\n"
        f"- Chart Pattern: {pattern_line if pattern_line else 'None'}\n"
        "\n"
        "### Market Data & Indicators\n"
        f"{json.dumps(market_data, ensure_ascii=False)}\n"
        f"{json.dumps(indicators_serializable, ensure_ascii=False)}\n"
        f"{json.dumps(indicators_m1_serializable, ensure_ascii=False)}\n"
        "\n"
        "### Decision Framework\n"
        "1. **Classify the market state as 'trend' or 'range'** using ADX, EMA, RSI, and Bollinger Bands:\n"
        "   - *Trend*: ADX > 25, clear EMA slope, price persistently above/below EMA or BB midline.\n"
        "   - *Range*: ADX < 25, flat EMA, price oscillates around EMA or BB midline.\n"
        "2. **LONG position:**\n"
        "   - HOLD if trend indicators (up EMA slope, ADX > 25, price upper BB) show ongoing strength.\n"
        "   - EXIT if RSI > 70 with price stalling at upper BB, or momentum weakens.\n"
        "3. **SHORT position:**\n"
        "   - HOLD if trend indicators (down EMA slope, ADX > 25, price lower BB) show ongoing strength.\n"
        "   - EXIT if RSI < 30 with price stalling at lower BB, or momentum weakens.\n"
        "4. **Post-entry stability:**\n"
        "   - Avoid exits within 5 minutes or ±5 pips of entry unless a clear reversal or major warning appears.\n"
        "5. **General:**\n"
        "   - Ignore minor fluctuations; do not exit on a single chart pattern or RSI alone.\n"
        "   - Consider EXIT only when at least two reversal signals align (e.g., pattern + EMA reversal, pattern + ADX drop).\n"
        "\n"
        "### Response Instructions\n"
        "- Output valid one-line JSON: {\"action\":\"EXIT\"|\"HOLD\",\"reason\":\"Concise reason, max 25 words\"}\n"
        "- Do not output anything except the JSON object.\n"
        "- Example: {\"action\":\"HOLD\",\"reason\":\"Upward EMA and strong ADX; trend likely to continue.\"}\n"
        "- Example: {\"action\":\"EXIT\",\"reason\":\"RSI overbought and price stalling at upper Bollinger Band.\"}\n"
    )
    try:
        response_json = ask_openai(prompt)
        log_prompt_response(
            "EXIT",
            instrument,
            prompt,
            json.dumps(response_json, ensure_ascii=False),
        )
    except Exception as exc:
        try:
            log_ai_decision("ERROR", instrument, str(exc))
        except Exception as log_exc:  # pragma: no cover
            logger.warning("log_ai_decision failed: %s", log_exc)
        raise
    _last_exit_ai_call_time = now
    try:
        log_ai_decision("EXIT", instrument, json.dumps(response_json, ensure_ascii=False))
    except Exception as exc:  # pragma: no cover - logging failure shouldn't stop flow
        logger.warning("log_ai_decision failed: %s", exc)
    logger.debug(f"[get_exit_decision] prompt sent:\n{prompt}")
    logger.info(f"OpenAI response: {response_json}")

    # --- Pattern direction consistency check -----------------------------
    try:
        action = str(response_json.get("action", "")).upper()
        reason_text = str(response_json.get("reason", "")).lower()
        if action == "EXIT":
            for pat, direction in PATTERN_DIRECTION.items():
                if pat in reason_text:
                    pos_dir = "bullish" if side == "LONG" else "bearish"
                    logger.info(
                        "exit_reason pattern=%s dir=%s pos_side=%s",
                        pat,
                        direction,
                        side,
                    )
                    if direction == pos_dir:
                        logger.warning(
                            "AI EXIT contradicted by pattern orientation; overriding to HOLD"
                        )
                        response_json["action"] = "HOLD"
                    break
    except Exception as exc:
        logger.error(f"pattern check failed: {exc}")

    # --- Trend consistency check -------------------------------------------
    try:
        if response_json.get("action", "").upper() == "EXIT":
            adx_series = indicators.get("adx")
            ema_fast_series = indicators.get("ema_fast")
            ema_slow_series = indicators.get("ema_slow")
            if adx_series is not None and ema_fast_series is not None:
                last_adx = (
                    float(adx_series.iloc[-1]) if hasattr(adx_series, "iloc") else float(adx_series[-1])
                )
                if last_adx >= adx_dynamic_thresh:
                    # Determine EMA slope over last 3 candles
                    if hasattr(ema_fast_series, "iloc") and len(ema_fast_series) >= 3:
                        ema_last = float(ema_fast_series.iloc[-1])
                        ema_prev = float(ema_fast_series.iloc[-3])
                    elif isinstance(ema_fast_series, (list, tuple)) and len(ema_fast_series) >= 3:
                        ema_last = float(ema_fast_series[-1])
                        ema_prev = float(ema_fast_series[-3])
                    else:
                        ema_last = None
                        ema_prev = None
                    if ema_last is not None and ema_prev is not None:
                        slope = ema_last - ema_prev
                        trend_cont = False
                        if side == "LONG" and slope > 0:
                            trend_cont = True
                        elif side == "SHORT" and slope < 0:
                            trend_cont = True
                        if trend_cont:
                            logger.warning(
                                "AI EXIT overridden: strong trend indicators in favor of current position"
                            )
                            response_json["action"] = "HOLD"
    except Exception as exc:
        logger.error(f"trend consistency check failed: {exc}")

    return response_json



# ----------------------------------------------------------------------
# TP / SL adjustment helper
# ----------------------------------------------------------------------
def get_tp_sl_adjustment(market_data, current_tp, current_sl):
    # TP/SL is now decided in get_trade_plan; no further adjustment needed.
    return "No adjustment"


# ----------------------------------------------------------------------
# Unified LLM call: regime → entry → TP/SL & probabilities
# ----------------------------------------------------------------------
def get_trade_plan(
    market_data: dict,
    indicators: dict[str, dict],
    candles_dict: dict[str, list],
    hist_stats: dict | None = None,
    patterns: list[str] | None = None,
    pattern_tf: str = "M5",
    detected_patterns: dict[str, str | None] | None = None,
    *,
    higher_tf_direction: str | None = None,
    allow_delayed_entry: bool | None = None,
    instrument: str | None = None,
    trade_mode: str | None = None,
    mode_reason: str | None = None,
    trend_prompt_bias: str | None = None,
    filter_ctx: dict | None = None,
) -> dict:
    """
    Single‑shot call to the LLM that returns a dict:
        {
          "regime": {...},
          "entry":  {...},
          "risk":   {...}
        }
    ``indicators`` should map timeframe labels (e.g. "M5", "M1") to their
    respective indicator dictionaries. ``candles_dict`` likewise contains a
    list of candles for each timeframe.

    ``higher_tf_direction`` conveys the trend direction of a higher timeframe and
    is included in the prompt so the model can avoid contradicting it.

    The function also performs local guards:
        • tp_prob ≥ MIN_TP_PROB
        • expected value (tp*tp_prob – sl*sl_prob) ≥ MIN_EXPECTED_VALUE
      If either guard fails, it forces ``side:"no"``.
    """
    if allow_delayed_entry is None:
        allow_delayed_entry = (
            env_loader.get_env("ALLOW_DELAYED_ENTRY", "true").lower() == "true"
        )

    if instrument is None:
        instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")

    ind_m5 = indicators.get("M5", {})
    ind_m1 = indicators.get("M1", {})
    ind_m15 = indicators.get("M15", {})
    ind_d1 = indicators.get("D1", indicators.get("D", {}))
    candles_m5 = candles_dict.get("M5", [])
    candles_m1 = candles_dict.get("M1", [])
    candles_m15 = candles_dict.get("M15", [])
    candles_d1 = candles_dict.get("D1", candles_dict.get("D", []))

    macro_summary = ""
    macro_sentiment = None
    try:
        macro = macro_analyzer.get_market_summary()
        macro_summary = macro.get("summary", "")
        macro_sentiment = macro.get("sentiment")
    except Exception:
        macro_summary = ""
        macro_sentiment = None

    pattern_name = None
    if patterns:
        try:
            tf_candles = candles_dict.get(pattern_tf, [])
            if USE_LOCAL_PATTERN:
                from backend.strategy.pattern_scanner import scan_all
                pattern_name = scan_all(tf_candles)
            else:
                pattern_res = detect_chart_pattern(tf_candles, patterns)
                pattern_name = pattern_res.get("pattern")
        except Exception:
            pattern_name = None

    pattern_line = None
    if detected_patterns:
        try:
            pattern_line = ", ".join(
                f"{tf}:{p}" for tf, p in detected_patterns.items() if p
            ) or None
        except Exception:
            pattern_line = str(detected_patterns)
    elif pattern_name:
        pattern_line = pattern_name

    # --- calculate noise and pullback state ------------------------------
    noise_pips = None
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        atr_series = ind_m5.get("atr")
        bb_upper = ind_m5.get("bb_upper")
        bb_lower = ind_m5.get("bb_lower")

        atr_val = None
        if atr_series is not None:
            if hasattr(atr_series, "iloc"):
                atr_val = float(atr_series.iloc[-1])
            else:
                atr_val = float(atr_series[-1])
        bw_val = None
        if bb_upper is not None and bb_lower is not None:
            if hasattr(bb_upper, "iloc"):
                bb_u = float(bb_upper.iloc[-1])
            else:
                bb_u = float(bb_upper[-1])
            if hasattr(bb_lower, "iloc"):
                bb_l = float(bb_lower.iloc[-1])
            else:
                bb_l = float(bb_lower[-1])
            bw_val = bb_u - bb_l

        atr_pips = atr_val / pip_size if atr_val is not None else 0.0
        bw_pips = bw_val / pip_size if bw_val is not None else 0.0
        noise_pips = max(atr_pips, bw_pips)
    except Exception:
        noise_pips = None

    # noise_pips を用いて動的な TP 達成確率下限を算出
    try:
        dynamic_min_tp_prob = max(DYN_TP_PROB_FLOOR, (noise_pips or 0) * 0.6)
        dynamic_min_tp_prob = min(dynamic_min_tp_prob, DYN_TP_PROB_CEIL)
    except Exception:
        dynamic_min_tp_prob = DYN_TP_PROB_CEIL

    noise_val = f"{noise_pips:.1f}" if noise_pips is not None else "N/A"
    tv_score = "N/A"

    comp_val = None

    recent_high = None
    recent_low = None
    try:
        highs = []
        lows = []
        for c in candles_m5[-20:]:
            if not isinstance(c, dict):
                continue
            if 'mid' in c:
                highs.append(float(c['mid']['h']))
                lows.append(float(c['mid']['l']))
            else:
                highs.append(float(c.get('h')))
                lows.append(float(c.get('l')))
        if highs and lows:
            recent_high = max(highs)
            recent_low = min(lows)
    except Exception:
        pass

    class _OneVal:
        def __init__(self, val):
            class _IL:
                def __getitem__(self, idx):
                    return val
            self.iloc = _IL()

    noise_series = _OneVal(noise_pips) if noise_pips is not None else None
    pullback_needed = calculate_dynamic_pullback(
        {**ind_m5, 'noise': noise_series}, recent_high or 0.0, recent_low or 0.0
    )
    pullback_done = False
    try:
        price = None
        if isinstance(market_data, dict):
            bid = market_data.get('bid')
            ask = market_data.get('ask')
            if bid is None and 'prices' in market_data:
                bid = market_data['prices'][0]['bids'][0]['price']
            if ask is None and 'prices' in market_data:
                ask = market_data['prices'][0]['asks'][0]['price']
            if higher_tf_direction == 'long' and bid is not None:
                price = float(bid)
            elif higher_tf_direction == 'short' and ask is not None:
                price = float(ask)
        if price is not None:
            from backend.strategy.dynamic_pullback import pullback_completed

            pullback_done = pullback_completed(
                higher_tf_direction or '',
                price,
                pullback_needed,
                recent_high or 0.0,
                recent_low or 0.0,
            )
    except Exception:
        pullback_done = False

    # --- 最新出来高比率を計算 --------------------------------------
    vol_ratio = None
    try:
        if candles_m5:
            last = candles_m5[-1]
            if not last.get('complete'):
                vol_last = float(last.get('volume', 0))
                prev_vols = [
                    float(c.get('volume', 0))
                    for c in candles_m5[:-1]
                    if c.get('complete')
                ][-6:]
                avg = sum(prev_vols) / len(prev_vols) if prev_vols else 0.0
                vol_ratio = (vol_last / avg) if avg else 1.0
    except Exception:
        vol_ratio = None



    prompt, comp_val = build_trade_plan_prompt(
        ind_m5,
        ind_m1,
        ind_m15,
        ind_d1,
        candles_m5,
        candles_m1,
        candles_m15,
        candles_d1,
        hist_stats,
        pattern_line,
        macro_summary,
        macro_sentiment,
        pullback_done=pullback_done,
        vol_ratio=vol_ratio,
        weight_last=ind_m5.get("weight_last"),
        allow_delayed_entry=allow_delayed_entry,
        higher_tf_direction=higher_tf_direction,
        trend_prompt_bias=trend_prompt_bias,
        trade_mode=trade_mode,
        summarize_candles=USE_CANDLE_SUMMARY,
    )
    try:
        raw = ask_openai(
            prompt, model=env_loader.get_env("AI_TRADE_MODEL", "gpt-4.1-nano")
        )
        log_prompt_response(
            "ENTRY",
            instrument,
            prompt,
            json.dumps(raw, ensure_ascii=False) if isinstance(raw, dict) else str(raw),
        )
    except Exception as exc:
        try:
            log_ai_decision("ERROR", instrument, str(exc))
        except Exception as log_exc:  # pragma: no cover
            logger.warning("log_ai_decision failed: %s", log_exc)
        raise

    # OpenAI から JSON 文字列が返ってきた場合に備えて辞書化
    try:
        raw = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as e:
        logging.warning("\u26a0\ufe0f JSON decode error: %s", e)
        return {"entry": {"side": "no"}, "raw": raw, "reason": "PARSE_FAIL"}
    try:
        log_ai_decision("ENTRY", instrument, json.dumps(raw, ensure_ascii=False))
    except Exception as exc:  # pragma: no cover - logging failure shouldn't stop flow
        logger.warning("log_ai_decision failed: %s", exc)
    try:
        from diagnostics import diagnostics as diag
        diag.log("entry", json.dumps(raw, ensure_ascii=False))
    except Exception:
        pass

    plan, err = parse_json_answer(raw)
    if plan is None:
        try:
            log_ai_decision("ERROR", instrument, json.dumps(raw, ensure_ascii=False))
        except Exception as exc:  # pragma: no cover - ignore logging failure
            logger.warning("log_ai_decision failed: %s", exc)
        logger.info("Invalid JSON response: %s", raw)
        return {"entry": {"side": "no"}, "raw": raw, "reason": "PARSE_FAIL"}
    if not _is_schema_valid(plan):
        try:
            raw_retry = ask_openai(prompt, model=env_loader.get_env("AI_TRADE_MODEL", "gpt-4.1-nano"))
            plan_retry, _ = parse_json_answer(raw_retry)
            if plan_retry and _is_schema_valid(plan_retry):
                plan = plan_retry
            else:
                logger.warning("Schema validation failed twice")
        except Exception:
            logger.warning("Retry after schema validation failed")

    # AIが返したレジーム情報を取り出す
    market_cond = plan.get("regime")

    if plan.get("entry", {}).get("side") == "no":
        why = plan.get("why") or plan.get("entry", {}).get("why")
        if isinstance(why, str) and why:
            plan["reason"] = why
        plan["entry"]["side"] = (
            market_cond.get("trend_direction") if market_cond else "long"
        )

    entry_conf = plan.get("entry_confidence")
    try:
        entry_conf = float(entry_conf) if entry_conf is not None else None
    except (TypeError, ValueError):
        entry_conf = None
    if entry_conf is None:
        side_planned = plan.get("entry", {}).get("side")
        probs = plan.get("probs")
        if isinstance(probs, dict) and side_planned in probs:
            try:
                vals = [float(v) for v in probs.values()]
                total = sum(vals)
                if not (0.9 <= total <= 1.1):
                    import math
                    e_vals = [math.exp(float(v)) for v in vals]
                    total = sum(e_vals)
                    norm = {k: math.exp(float(v)) / total for k, v in probs.items()}
                    entry_conf = float(norm.get(side_planned))
                else:
                    entry_conf = float(probs.get(side_planned))
            except Exception:
                entry_conf = None
    side_planned = plan.get("entry", {}).get("side")
    if entry_conf is not None and higher_tf_direction in ("long", "short") and side_planned in ("long", "short"):
        if (higher_tf_direction == "long" and side_planned == "short") or (higher_tf_direction == "short" and side_planned == "long"):
            entry_conf = max(0.0, entry_conf - 0.3)

    if entry_conf is None:
        entry_conf = 0.5
    entry_type = _classify_entry_type(market_cond, pullback_done)
    entry_conf = _apply_entry_type_boost(entry_conf, entry_type)
    plan["entry_confidence"] = entry_conf
    plan["entry_type"] = entry_type

    # LLMが反守方向を出した場合の後処理
    try:
        regime = market_cond.get("market_condition") if market_cond else None
        if regime == "trend" and plan.get("entry_type") == "reversal":
            plan["entry_type"] = "trend"
            probs = plan.get("probs", {})
            if "long" in probs and "short" in probs:
                probs["long"], probs["short"] = probs["short"], probs["long"]
            plan["probs"] = probs
    except Exception:
        pass

    # ---- local guards -------------------------------------------------
    risk = risk_autofix(plan.get("risk"))
    plan["risk"] = risk
    entry = plan.get("entry", {})
    mode = entry.get("mode", "market")
    if mode not in ("market", "limit", "wait"):
        entry["mode"] = "market"
    if risk:
        try:
            tp = float(risk.get("tp_pips", 8))
            sl = float(risk.get("sl_pips", 4))
            p = float(risk.get("tp_prob", 0.6))
            q = float(risk.get("sl_prob", 0.4))
            spread = float(market_data.get("spread_pips", 0))

            noise_sl_mult = float(env_loader.get_env("NOISE_SL_MULT", "1.5"))
            sl *= noise_sl_mult
            min_sl = float(env_loader.get_env("MIN_SL_PIPS", "0"))

            # --- 動的SL下限を計算して適用 -------------------------
            try:
                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                atr_series = ind_m5.get("atr")
                atr_val = None
                if atr_series is not None:
                    atr_val = (
                        float(atr_series.iloc[-1])
                        if hasattr(atr_series, "iloc")
                        else float(atr_series[-1])
                    )
                atr_pips = atr_val / pip_size if atr_val is not None else None

                side = entry.get("side", "no")
                bid = market_data.get("bid")
                ask = market_data.get("ask")
                entry_price = (
                    float(bid) if side == "long" else float(ask)
                ) if bid is not None and ask is not None else None
                swing_diff = None
                if entry_price is not None:
                    swing_diff = get_recent_swing_diff(
                        candles_m5,
                        side,
                        entry_price,
                        pip_size,
                    )
                session_factor = 1.3 if is_high_vol_session() else 1.0
                dynamic_sl = calc_min_sl(
                    atr_pips,
                    swing_diff,
                    atr_mult=float(env_loader.get_env("MIN_ATR_MULT", "1.2")),
                    swing_buffer_pips=5.0,
                    session_factor=session_factor,
                )
                sl = max(sl, dynamic_sl, min_sl, MIN_ABS_SL_PIPS)
            except Exception:
                sl = max(sl, min_sl, MIN_ABS_SL_PIPS)

            risk["sl_pips"] = sl

            if p < 0 or p > 1 or q < 0 or q > 1:
                logger.warning("Probability out of range - clamping to [0,1]")
                p = max(0.0, min(1.0, p))
                q = max(0.0, min(1.0, q))
                risk["tp_prob"] = p
                risk["sl_prob"] = q

            p, q = normalize_probs(p, q)
            risk["tp_prob"] = p
            risk["sl_prob"] = q
            total = p + q
            if total > 1.0 + PROB_MARGIN or total < 1.0 - PROB_MARGIN:
                logger.warning("Probabilities invalid — adjusting")
                if total > 0:
                    p /= total
                    q /= total
                else:
                    p, q = 0.6, 0.4
                risk["tp_prob"] = p
                risk["sl_prob"] = q
                total = p + q
            if total > 1.0 + PROB_MARGIN or total < 1.0 - PROB_MARGIN:
                logger.warning("Probabilities still invalid — skipping plan")
                logger.info("Plan with invalid probabilities: %s", json.dumps(plan, ensure_ascii=False))
                plan["entry"]["side"] = "no"
                plan["reason"] = "PROB_INVALID"
                return plan

            min_net = MIN_NET_TP_PIPS
            if noise_pips is not None:
                try:
                    min_net = max(min_net, noise_pips * 0.6)
                except Exception:
                    pass
            if (tp - spread) < min_net:
                plan["entry"]["side"] = "no"
                plan.setdefault("reason", "NET_TP_TOO_SMALL")
        except (TypeError, ValueError):
            plan["entry"]["side"] = "no"
            plan["risk"] = {}
            plan["reason"] = "RISK_PARSE_FAIL"
            return plan

        if p < dynamic_min_tp_prob or (tp * p - sl * q) < MIN_EXPECTED_VALUE:
            plan["entry"]["side"] = "no"
            plan.setdefault("reason", "PROB_TOO_LOW")

    # Composite score 判定を完全にスキップ

    if plan.get("entry", {}).get("side") == "no":
        plan["risk"] = {}

    # ADX no-trade zone enforcement (skipped when ENABLE_RANGE_ENTRY is true)
    try:
        adx_series = ind_m5.get("adx")
        if hasattr(adx_series, "iloc"):
            adx_val = float(adx_series.iloc[-1])
        else:
            adx_val = float(adx_series[-1])
        if (
            not ENABLE_RANGE_ENTRY
            and ADX_NO_TRADE_MIN <= adx_val <= ADX_NO_TRADE_MAX
            and not pattern_name
        ):
            plan["entry"]["side"] = "no"
            plan.setdefault("reason", "ADX_NO_TRADE")
    except (TypeError, ValueError, IndexError):
        pass

    # Narrow Bollinger Band override: switch to market on volatility spike
    try:
        bb_upper = ind_m5.get("bb_upper")
        bb_lower = ind_m5.get("bb_lower")
        if bb_upper is not None and bb_lower is not None and len(bb_upper) and len(bb_lower):
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            bw_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size
            bw_thresh = float(env_loader.get_env("BAND_WIDTH_THRESH_PIPS", "4"))
            if bw_pips <= bw_thresh:
                lookback = 3
                adx_spike = False
                atr_spike = False
                adx_series = ind_m5.get("adx")
                if adx_series is not None and len(adx_series) > lookback:
                    adx_last = float(adx_series.iloc[-1]) if hasattr(adx_series, "iloc") else float(adx_series[-1])
                    adx_prev = float(adx_series.iloc[-lookback-1]) if hasattr(adx_series, "iloc") else float(adx_series[-lookback-1])
                    if adx_prev > 0 and adx_last / adx_prev >= VOL_SPIKE_ADX_MULT:
                        adx_spike = True
                atr_series = ind_m5.get("atr")
                if atr_series is not None and len(atr_series) > lookback:
                    atr_last = float(atr_series.iloc[-1]) if hasattr(atr_series, "iloc") else float(atr_series[-1])
                    atr_prev = float(atr_series.iloc[-lookback-1]) if hasattr(atr_series, "iloc") else float(atr_series[-lookback-1])
                    if atr_prev > 0 and atr_last / atr_prev >= VOL_SPIKE_ATR_MULT:
                        atr_spike = True
                if adx_spike or atr_spike:
                    plan.setdefault("entry", {})["mode"] = "market"
    except Exception:
        pass

    # --- Ensure side is long or short ---------------------------------
    side_val = plan.get("entry", {}).get("side")
    if side_val not in ("long", "short"):
        probs = plan.get("probs", {}) or {}
        try:
            long_p = float(probs.get("long", 0))
            short_p = float(probs.get("short", 0))
        except Exception:
            long_p = short_p = 0.0
        if long_p > short_p:
            forced = "long"
        elif short_p > long_p:
            forced = "short"
        elif higher_tf_direction in ("long", "short"):
            forced = higher_tf_direction
        else:
            forced = "long"
        plan.setdefault("entry", {})["side"] = forced

    return plan


# ----------------------------------------------------------------------
# Recent candle bias helper
# ----------------------------------------------------------------------
def is_entry_blocked_by_recent_candles(side: str, candles: list) -> bool:
    """最近のローソク足が反対方向の強いシグナルを示す場合にTrueを返す。"""
    lookback = int(env_loader.get_env("REV_BLOCK_BARS", "3"))
    tail_thr = float(env_loader.get_env("TAIL_RATIO_BLOCK", "2.0"))
    vol_period = int(env_loader.get_env("VOL_SPIKE_PERIOD", "5"))

    if lookback <= 0 or not candles:
        return False

    volumes = []
    for c in candles[-(vol_period + lookback):]:
        try:
            volumes.append(float(c.get("volume", 0)))
        except Exception:
            volumes.append(0.0)
    vol_sma = compute_volume_sma(volumes, vol_period)

    for c in reversed(candles[-lookback:]):
        feats = get_candle_features(c, volume_sma=vol_sma)
        should_block = feats["vol_spike"] and feats["tail_ratio"] >= tail_thr
        if should_block:
            try:
                mid = c.get("mid", {})
                o = float(mid.get("o", c.get("o")))
                cl = float(mid.get("c", c.get("c")))
            except Exception:
                continue
            direction = "long" if cl > o else "short" if cl < o else None
            if direction and direction != side:
                logging.debug(
                    "Recent candle suggests %s (tail %.2f, vol spike %s)",
                    direction,
                    feats["tail_ratio"],
                    feats["vol_spike"],
                )
                return True
    return False


# ----------------------------------------------------------------------
# AI-based exit decision
# ----------------------------------------------------------------------
# Legacy evaluate_exit functionality now lives in ``exit_ai_decision``.


def should_convert_limit_to_market(context: dict) -> bool:
    """
    OpenAI に問い合わせてリミット注文を成行に変更すべきか判断する。

    context には ATR や ADX のほか、RSI、EMA 傾き、ボリンジャーバンド幅
    などを含めることができる。
    """
    prompt = (
        "We placed a limit order that has not filled and price is moving away.\n"
        "Use ATR, ADX, RSI, EMA slope and Bollinger band width from the context "
        "below to decide if switching to a market order is reasonable.\n\n"
        f"Context: {json.dumps(context, ensure_ascii=False)}\n\n"
        "Should we cancel the limit order and place a market order instead?\n"
        "Respond with YES or NO."
    )
    try:
        result = ask_openai(prompt, model=AI_LIMIT_CONVERT_MODEL)
        log_prompt_response(
            "LIMIT_CONVERT",
            env_loader.get_env("DEFAULT_PAIR", "USD_JPY"),
            prompt,
            json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result),
        )
    except Exception as exc:
        logger.warning(f"should_convert_limit_to_market failed: {exc}")
        return False

    text = json.dumps(result) if isinstance(result, dict) else str(result)
    return text.strip().upper().startswith("YES")



logger.info("OpenAI Analysis finished")

# Exports
__all__ = [
    "get_ai_cooldown_sec",
    "get_entry_decision",
    "get_exit_decision",
    "get_tp_sl_adjustment",
    "get_market_condition",
    "get_trade_plan",
    "AIDecision",
    "evaluate_exit",
    "should_convert_limit_to_market",
    "is_entry_blocked_by_recent_candles",
    "LIMIT_THRESHOLD_ATR_RATIO",
    "MAX_LIMIT_AGE_SEC",
    "MIN_NET_TP_PIPS",
    "COOL_BBWIDTH_PCT",
    "COOL_ATR_PCT",
    "ADX_NO_TRADE_MIN",
    "ADX_NO_TRADE_MAX",
    "EXIT_BIAS_FACTOR",
    "LOCAL_WEIGHT_THRESHOLD",
    "IGNORE_REGIME_CONFLICT",
    "ADX_SLOPE_LOOKBACK",
    "ENABLE_RANGE_ENTRY",
    "calc_consistency",
    "_apply_entry_type_boost",
    "_classify_entry_type",
]
