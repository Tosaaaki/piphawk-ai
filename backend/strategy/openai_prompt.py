"""Prompt generation utilities for OpenAI analysis."""
from __future__ import annotations

import json
from typing import Tuple

from backend.utils import env_loader
from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
from backend.utils.prompt_loader import load_template

MIN_TP_PROB = float(env_loader.get_env("MIN_TP_PROB", "0.75"))
TP_PROB_HOURS = int(env_loader.get_env("TP_PROB_HOURS", "24"))
MIN_RRR = float(env_loader.get_env("MIN_RRR", "0.8"))
MIN_NET_TP_PIPS = float(env_loader.get_env("MIN_NET_TP_PIPS", "1"))
TREND_ADX_THRESH = float(env_loader.get_env("TREND_ADX_THRESH", "20"))
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

def _instruction_text() -> str:
    """Return formatted instruction section."""
    return INSTRUCTION_TEMPLATE.format(
        TP_PROB_HOURS=TP_PROB_HOURS,
        MIN_TP_PROB=MIN_TP_PROB,
        MIN_RRR=MIN_RRR,
        MIN_NET_TP_PIPS=MIN_NET_TP_PIPS,
    )


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
) -> Tuple[str, float | None]:
    """Return the prompt string for ``get_trade_plan`` and the composite score."""
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

    prompt = mode_header + f"""
⚠️【Market Regime Classification – Flexible Criteria】
Classify as "TREND" if ANY TWO of the following conditions are met:
- ADX ≥ {TREND_ADX_THRESH} maintained over at least the last 3 candles.
- EMA consistently sloping upwards or downwards without major reversals within the last 3 candles.
- Price consistently outside the Bollinger Band midline (above for bullish, below for bearish).

If these conditions are not clearly met, classify the market as "RANGE".
{RANGE_ENTRY_NOTE}

🚫【Counter-trend Trade Prohibition】
Under clearly identified TREND conditions, avoid counter-trend trades and never rely solely on RSI extremes. Treat pullbacks as trend continuation. However, if a strong reversal pattern such as a double top/bottom or head-and-shoulders is detected and ADX is turning down, a small counter-trend position is acceptable.

🔄【Counter-Trend Trade Allowance】
Allow short-term counter-trend trades only when all of the following are true:
- ADX ≤ {TREND_ADX_THRESH} or clearly declining.
- A clear reversal pattern (double top/bottom, head-and-shoulders) is present.
- RSI ≤ 30 for LONG or ≥ 70 for SHORT, showing potential exhaustion.
- Price action has stabilized with minor reversal candles.
- TP kept small (5–10 pips) and risk tightly controlled.

Price has just printed multiple upper shadows and ADX(S10) fell >30% from its peak.
Evaluate if a short scalp is favorable given potential exhaustion.

📈【Trend Entry Clarification】
Once a TREND is confirmed, prioritize entries on pullbacks. Use recent volatility (ATR or Bollinger width) to gauge the pullback depth. Shorts enter after price rises {pullback_needed:.1f} pips above the latest low, longs after price drops {pullback_needed:.1f} pips below the latest high. This pullback rule overrides RSI extremes.{no_pullback_msg}""" + (
        "\n\n⏳【Trend Overshoot Handling】\n"
        "When RSI exceeds 70 in an uptrend or falls below 30 in a downtrend, do not immediately set side to 'no'.\n"
        "If momentum is still strong you may follow the trend. Otherwise respond with mode:'wait' so the system rechecks after a pullback of about {pullback_needed:.1f} pips.\n"
        if allow_delayed_entry else ""
    ) + f"""

🔎【Minor Retracement Clarification】
Do not interpret short-term retracements as trend reversals. Genuine trend reversals require ALL of the following simultaneously:
- EMA direction reversal sustained for at least 3 candles.
- ADX clearly drops below {TREND_ADX_THRESH}, indicating weakening trend momentum.

🎯【Improved Exit Strategy】
Avoid exiting during normal trend pullbacks. Only exit a trend trade if **ALL** of the following are true:
- EMA reverses direction and this is sustained for at least 3 consecutive candles.
- ADX drops clearly below {TREND_ADX_THRESH}, showing momentum has faded.
If these are not all met, HOLD the position even if RSI is extreme or price briefly retraces.

♻️【Immediate Re-entry Policy】
If a stop-loss is triggered but original trend conditions remain intact (ADX≥{TREND_ADX_THRESH}, clear EMA slope), immediately re-enter in the same direction upon the next valid signal.

### Recent Indicators (last 20 values each)
## M5
RSI  : {_series_tail_list(ind_m5.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_m5.get('atr'), 20)}
ADX  : {_series_tail_list(ind_m5.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_m5.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_m5.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_m5.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_m5.get('ema_slow'), 20)}

## M15
RSI  : {_series_tail_list(ind_m15.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_m15.get('atr'), 20)}
ADX  : {_series_tail_list(ind_m15.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_m15.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_m15.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_m15.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_m15.get('ema_slow'), 20)}

## M1
RSI  : {_series_tail_list(ind_m1.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_m1.get('atr'), 20)}
ADX  : {_series_tail_list(ind_m1.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_m1.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_m1.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_m1.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_m1.get('ema_slow'), 20)}

## D1
RSI  : {_series_tail_list(ind_d1.get('rsi'), 20)}
ATR  : {_series_tail_list(ind_d1.get('atr'), 20)}
ADX  : {_series_tail_list(ind_d1.get('adx'), 20)}
BB_hi: {_series_tail_list(ind_d1.get('bb_upper'), 20)}
BB_lo: {_series_tail_list(ind_d1.get('bb_lower'), 20)}
EMA_f: {_series_tail_list(ind_d1.get('ema_fast'), 20)}
EMA_s: {_series_tail_list(ind_d1.get('ema_slow'), 20)}

### M5 Candles
{candles_m5[-50:]}

### M15 Candles
{candles_m15[-30:]}

### M1 Candles
{candles_m1[-20:]}

### D1 Candles
{candles_d1[-60:]}

{adx_snapshot}{pattern_text}{direction_line}
### How to use the provided candles:
- Use the medium-term view (50 candles) to understand the general market trend, key support/resistance levels, and to avoid noisy, short-lived moves.
- Use the short-term view (20 candles) specifically for optimizing entry timing (such as waiting for pullbacks or breakouts) and to confirm recent price momentum.

### 90-day Historical Stats
{json.dumps(hist_stats or {}, separators=(',', ':'))}

### Estimated Noise
{noise_val} pips is the approximate short-term market noise.
Use this as a baseline for setting wider stop-loss levels.
After calculating TP hit probability, widen the SL by at least {env_loader.get_env("NOISE_SL_MULT", "1.5")} times.

### Composite Trend Score
{tv_score}

### Pivot Levels
Pivot: {ind_m5.get('pivot')}, R1: {ind_m5.get('pivot_r1')}, S1: {ind_m5.get('pivot_s1')}

### N-Wave Target
{ind_m5.get('n_wave_target')}

### Volume Ratio
{f"{vol_ratio:.2f}" if vol_ratio is not None else 'N/A'}

### Weight Last
{f"{weight_last:.2f}" if weight_last is not None else 'N/A'}

### Pullback Completed
{pullback_done}

### Macro News Summary
{macro_summary if macro_summary else 'N/A'}
### Macro Sentiment
{macro_sentiment if macro_sentiment else 'N/A'}

""" + _instruction_text()
    bias = trend_prompt_bias or TREND_PROMPT_BIAS
    bias_note = ""
    if bias == "aggressive":
        # 条件が曖昧な場合でも積極的にポジションを示すよう指示
        bias_note = (
            "\nBe strongly proactive: unless risk rules clearly prohibit, choose 'long' or 'short' instead of 'no'. "
            "Return 'no' only when absolutely no valid setup exists."
        )
    prompt += bias_note
    return prompt, comp_val
