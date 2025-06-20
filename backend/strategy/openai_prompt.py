"""Prompt generation utilities for OpenAI analysis."""
from __future__ import annotations

import json
from typing import Tuple

from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
from backend.utils import env_loader
from backend.utils.prompt_loader import load_template

MIN_TP_PROB = float(env_loader.get_env("MIN_TP_PROB", "0.75"))
TP_PROB_HOURS = int(env_loader.get_env("TP_PROB_HOURS", "24"))
MIN_RRR = float(env_loader.get_env("MIN_RRR", "0.8"))
MIN_NET_TP_PIPS = float(env_loader.get_env("MIN_NET_TP_PIPS", "1"))
TREND_ADX_THRESH = float(
    env_loader.get_env("TREND_ADX_THRESH", env_loader.get_env("ADX_TREND_THR", "20"))
)
TREND_PROMPT_BIAS = env_loader.get_env("TREND_PROMPT_BIAS", "normal").lower()
# レンジ相場でのトレード方針を任意に追記できる環境変数
RANGE_ENTRY_NOTE = env_loader.get_env(
    "RANGE_ENTRY_NOTE",
    (
        "When the market is RANGE, consider quick trades near Bollinger Band edges with small targets.\n"
        "### Micro-range step-down handling\n"
        "If market_state == \"micro_downtrend\":\n"
        "  • Treat each micro range (width ≤ 0.6*atr5) as 'box'.\n"
        "  • Short only:\n"
        "    - on retest of box_high −2 pips OR\n"
        "    - on breakout below box_low −1 pip with vol_burst ≥1.5\n"
        "  • Do NOT long unless price closes above 2 consecutive box_high levels.\n"
        "Return \"NoTrade\" when price is inside mid-zone of the box (±30%)."
    ),
)

# 共通のタスク指示文テンプレートを外部ファイルから読み込む
INSTRUCTION_TEMPLATE = load_template("trade_plan.txt")
# 新しいトレードプランテンプレート
TRADE_PLAN_PROMPT = load_template("trade_plan_instruction.txt")

# デフォルトの指標・ローソク足履歴本数
DEFAULT_PROMPT_TAIL_LEN = 20
DEFAULT_PROMPT_CANDLE_LEN = 20

def _instruction_text() -> str:
    """Return formatted instruction section."""
    return INSTRUCTION_TEMPLATE.format(
        TP_PROB_HOURS=TP_PROB_HOURS,
        MIN_TP_PROB=MIN_TP_PROB,
        MIN_RRR=MIN_RRR,
        MIN_NET_TP_PIPS=MIN_NET_TP_PIPS,
    )


def _series_tail_list(series, n: int = DEFAULT_PROMPT_TAIL_LEN) -> list:
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


def _candles_summary(candles: list) -> dict:
    """Return OHLC averages and last values for a candle list."""
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    for c in candles:
        if not isinstance(c, dict):
            continue
        v = c.get("mid", c)
        try:
            opens.append(float(v.get("o")))
            highs.append(float(v.get("h")))
            lows.append(float(v.get("l")))
            closes.append(float(v.get("c")))
        except Exception:
            continue
    if not opens:
        return {}
    def _avg(vals: list[float]) -> float:
        return sum(vals) / len(vals)

    return {
        "open_avg": _avg(opens),
        "high_avg": _avg(highs),
        "low_avg": _avg(lows),
        "close_avg": _avg(closes),
        "open_last": opens[-1],
        "high_last": highs[-1],
        "low_last": lows[-1],
        "close_last": closes[-1],
    }


def build_trade_plan_prompt(
    ind_m5: dict,
    ind_m1: dict,
    ind_m15: dict,
    ind_d1: dict,
    candles_m5: list,
    candles_m1: list,
    candles_m15: list,
    candles_d1: list,
    hist_stats: dict | None,
    pattern_line: str | None,
    macro_summary: str | None = None,
    macro_sentiment: str | None = None,
    pullback_done: bool = False,
    *,
    vol_ratio: float | None = None,
    weight_last: float | None = None,
    allow_delayed_entry: bool = False,
    higher_tf_direction: str | None = None,
    trend_prompt_bias: str | None = None,
    trade_mode: str | None = None,
    summarize_candles: bool = False,
) -> Tuple[str, float | None]:
    """Return the prompt string for ``get_trade_plan`` and the composite score."""
    tail_len = int(
        env_loader.get_env("PROMPT_TAIL_LEN", str(DEFAULT_PROMPT_TAIL_LEN))
    )
    candle_len = int(
        env_loader.get_env("PROMPT_CANDLE_LEN", str(DEFAULT_PROMPT_CANDLE_LEN))
    )
    # --------------------------------------------------------------
    # summarize candle statistics when requested
    # --------------------------------------------------------------
    candle_summary_str = "N/A"
    if summarize_candles:
        summary = {
            "m5": _candles_summary(candles_m5),
            "m15": _candles_summary(candles_m15),
            "m1": _candles_summary(candles_m1),
            "d1": _candles_summary(candles_d1),
        }
        candle_summary_str = json.dumps(summary, separators=(",", ":"))
    # --------------------------------------------------------------
    # Estimate market "noise" from ATR and Bollinger band width
    # --------------------------------------------------------------
    noise_pips = None
    try:
        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
        atr_series = ind_m5.get("atr")
        bb_upper = ind_m5.get("bb_upper")
        bb_lower = ind_m5.get("bb_lower")

        atr_val = None
        if atr_series is not None:
            atr_val = (
                float(atr_series.iloc[-1])
                if hasattr(atr_series, "iloc")
                else float(atr_series[-1])
            )
        bw_val = None
        if bb_upper is not None and bb_lower is not None:
            bb_u = float(bb_upper.iloc[-1]) if hasattr(bb_upper, "iloc") else float(bb_upper[-1])
            bb_l = float(bb_lower.iloc[-1]) if hasattr(bb_lower, "iloc") else float(bb_lower[-1])
            bw_val = bb_u - bb_l
        atr_pips = atr_val / pip_size if atr_val is not None else 0.0
        bw_pips = bw_val / pip_size if bw_val is not None else 0.0
        noise_pips = max(atr_pips, bw_pips)
    except Exception:
        noise_pips = None

    noise_val = f"{noise_pips:.1f}" if noise_pips is not None else "N/A"
    tv_score = "N/A"
    comp_val = None
    try:
        from backend.indicators.adx import calculate_adx_bb_score

        adx_series = ind_m5.get("adx")
        bb_upper = ind_m5.get("bb_upper")
        bb_lower = ind_m5.get("bb_lower")
        if adx_series is not None and bb_upper is not None and bb_lower is not None:
            comp_val = calculate_adx_bb_score(adx_series, bb_upper, bb_lower)
            tv_score = f"{comp_val:.2f}"
    except Exception:
        tv_score = "N/A"
        comp_val = None

    # --- calculate dynamic pullback threshold ----------------------------
    recent_high = None
    recent_low = None
    try:
        highs: list[float] = []
        lows: list[float] = []
        for c in candles_m5[-20:]:
            if not isinstance(c, dict):
                continue
            if "mid" in c:
                highs.append(float(c["mid"]["h"]))
                lows.append(float(c["mid"]["l"]))
            else:
                highs.append(float(c.get("h")))
                lows.append(float(c.get("l")))
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
    pullback_needed = calculate_dynamic_pullback({**ind_m5, "noise": noise_series}, recent_high or 0.0, recent_low or 0.0)

    pattern_text = f"\n### Detected Chart Pattern\n{pattern_line}\n" if pattern_line else "\n### Detected Chart Pattern\nNone\n"

    no_pullback_msg = ""
    try:
        adx_series = ind_m5.get("adx")
        allow_no_pb = float(env_loader.get_env("ALLOW_NO_PULLBACK_WHEN_ADX", "0"))
        if allow_no_pb > 0 and adx_series is not None and len(adx_series):
            adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
            if float(adx_val) >= allow_no_pb:
                no_pullback_msg = "\nPullback not required when ADX is high."
    except Exception:
        pass

    adx_last = None
    adx_avg3 = None
    try:
        adx_series = ind_m5.get("adx")
        if adx_series is not None and len(adx_series):
            adx_last = (
                float(adx_series.iloc[-1]) if hasattr(adx_series, "iloc") else float(adx_series[-1])
            )
            if len(adx_series) >= 3:
                if hasattr(adx_series, "iloc"):
                    adx_avg3 = float(sum(adx_series.iloc[-3:]) / 3)
                else:
                    adx_avg3 = float(sum(adx_series[-3:]) / 3)
    except Exception:
        adx_last = None
        adx_avg3 = None

    # 上位足のトレンド方向を明示的に記載
    direction_line = (
        "\n### Higher Timeframe Direction\n" + str(higher_tf_direction) + "\n"
        if higher_tf_direction
        else ""
    )

    adx_last_val = f"{adx_last:.2f}" if adx_last is not None else "N/A"
    adx_avg3_val = f"{adx_avg3:.2f}" if adx_avg3 is not None else "N/A"
    adx_snapshot = f"\n### ADX Snapshot\nlast:{adx_last_val}, last3_avg:{adx_avg3_val}\n"

    mode_header = f"### TRADING_MODE\n{trade_mode}\n" if trade_mode else ""

    overshoot = ""
    if allow_delayed_entry:
        overshoot = (
            "\n\n⏳【Trend Overshoot Handling】\n"
            "When RSI exceeds 70 in an uptrend or falls below 30 in a downtrend, do not immediately set side to 'no'.\n"
            f"If momentum is still strong you may follow the trend. Otherwise respond with mode:'wait' so the system rechecks after a pullback of about {pullback_needed:.1f} pips.\n"
        )

    values = dict(
        TREND_ADX_THRESH=TREND_ADX_THRESH,
        RANGE_ENTRY_NOTE=RANGE_ENTRY_NOTE,
        MIN_RRR=MIN_RRR,
        pullback_needed=pullback_needed,
        no_pullback_msg=no_pullback_msg,
        TREND_OVERSHOOT_SECTION=overshoot,
        m5_rsi=_series_tail_list(ind_m5.get("rsi"), tail_len),
        m5_atr=_series_tail_list(ind_m5.get("atr"), tail_len),
        m5_adx=_series_tail_list(ind_m5.get("adx"), tail_len),
        m5_bb_u=_series_tail_list(ind_m5.get("bb_upper"), tail_len),
        m5_bb_l=_series_tail_list(ind_m5.get("bb_lower"), tail_len),
        m5_ema_f=_series_tail_list(ind_m5.get("ema_fast"), tail_len),
        m5_ema_s=_series_tail_list(ind_m5.get("ema_slow"), tail_len),
        m15_rsi=_series_tail_list(ind_m15.get("rsi"), tail_len),
        m15_atr=_series_tail_list(ind_m15.get("atr"), tail_len),
        m15_adx=_series_tail_list(ind_m15.get("adx"), tail_len),
        m15_bb_u=_series_tail_list(ind_m15.get("bb_upper"), tail_len),
        m15_bb_l=_series_tail_list(ind_m15.get("bb_lower"), tail_len),
        m15_ema_f=_series_tail_list(ind_m15.get("ema_fast"), tail_len),
        m15_ema_s=_series_tail_list(ind_m15.get("ema_slow"), tail_len),
        m1_rsi=_series_tail_list(ind_m1.get("rsi"), tail_len),
        m1_atr=_series_tail_list(ind_m1.get("atr"), tail_len),
        m1_adx=_series_tail_list(ind_m1.get("adx"), tail_len),
        m1_bb_u=_series_tail_list(ind_m1.get("bb_upper"), tail_len),
        m1_bb_l=_series_tail_list(ind_m1.get("bb_lower"), tail_len),
        m1_ema_f=_series_tail_list(ind_m1.get("ema_fast"), tail_len),
        m1_ema_s=_series_tail_list(ind_m1.get("ema_slow"), tail_len),
        d1_rsi=_series_tail_list(ind_d1.get("rsi"), tail_len),
        d1_atr=_series_tail_list(ind_d1.get("atr"), tail_len),
        d1_adx=_series_tail_list(ind_d1.get("adx"), tail_len),
        d1_bb_u=_series_tail_list(ind_d1.get("bb_upper"), tail_len),
        d1_bb_l=_series_tail_list(ind_d1.get("bb_lower"), tail_len),
        d1_ema_f=_series_tail_list(ind_d1.get("ema_fast"), tail_len),
        d1_ema_s=_series_tail_list(ind_d1.get("ema_slow"), tail_len),
        candles_m5_tail=candles_m5[-candle_len:],
        candles_m15_tail=candles_m15[-candle_len:],
        candles_m1_tail=candles_m1[-candle_len:],
        candles_d1_tail=candles_d1[-candle_len:],
        candle_summary=candle_summary_str,
        adx_snapshot=adx_snapshot,
        pattern_text=pattern_text,
        direction_line=direction_line,
        hist_stats_json=json.dumps(hist_stats or {}, separators=(",", ":")),
        noise_val=noise_val,
        noise_sl_mult=env_loader.get_env("NOISE_SL_MULT", "1.5"),
        tv_score=tv_score,
        pivot=ind_m5.get("pivot"),
        pivot_r1=ind_m5.get("pivot_r1"),
        pivot_s1=ind_m5.get("pivot_s1"),
        n_wave_target=ind_m5.get("n_wave_target"),
        vol_ratio_formatted=f"{vol_ratio:.2f}" if vol_ratio is not None else "N/A",
        weight_last_formatted=f"{weight_last:.2f}" if weight_last is not None else "N/A",
        pullback_done=pullback_done,
        macro_summary_formatted=macro_summary if macro_summary else "N/A",
        macro_sentiment_formatted=macro_sentiment if macro_sentiment else "N/A",
    )

    from collections import defaultdict

    prompt = mode_header + TRADE_PLAN_PROMPT.format_map(defaultdict(str, values))
    prompt += _instruction_text()
    # scalp_momentum/micro_scalp モードでは常に積極的バイアスを使用
    if trade_mode in ("scalp_momentum", "micro_scalp"):
        bias = "aggressive"
    else:
        bias = trend_prompt_bias or TREND_PROMPT_BIAS
    bias_note = ""
    if bias == "aggressive":
        # 条件が曖昧な場合でも積極的にポジションを示すよう指示
        # "sell" を併記しているのはショートを意味することを明確にするため
        bias_note = (
            "\nBe strongly proactive: unless risk rules clearly prohibit, choose 'long' or 'short (sell)' instead of 'no'. "
            "Return 'no' only when absolutely no valid setup exists."
        )
    prompt += bias_note
    return prompt, comp_val
