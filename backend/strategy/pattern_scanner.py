from __future__ import annotations

"""Utility functions for simple chart pattern detection."""

import pandas as pd


# ----------------------------------------------------------------------
#  Primitive pattern detectors
# ----------------------------------------------------------------------

def is_doji(df: pd.DataFrame, *, body_ratio: float = 0.1) -> pd.Series:
    """Return a boolean Series marking Doji candles.

    Calculation is done per-row so the function works even when ``pandas`` is
    stubbed during testing.
    """
    open_list = list(df["open"])
    close_list = list(df["close"])
    high_list = list(df["high"])
    low_list = list(df["low"])

    flags = []
    for o, c, h, l in zip(open_list, close_list, high_list, low_list):
        rng = h - l
        if rng == 0:
            flags.append(False)
        else:
            flags.append(abs(c - o) / rng <= body_ratio)

    return pd.Series(flags, index=getattr(df, "index", range(len(flags))))


def _local_max(series: pd.Series) -> pd.Series:
    data = list(series)
    flags = [False] * len(data)
    for i in range(1, len(data) - 1):
        if data[i] is None:
            continue
        prev_v = data[i - 1]
        next_v = data[i + 1]
        if prev_v is not None and next_v is not None:
            if data[i] > prev_v and data[i] > next_v:
                flags[i] = True
    return pd.Series(flags, index=getattr(series, "index", range(len(flags))))


def _local_min(series: pd.Series) -> pd.Series:
    data = list(series)
    flags = [False] * len(data)
    for i in range(1, len(data) - 1):
        if data[i] is None:
            continue
        prev_v = data[i - 1]
        next_v = data[i + 1]
        if prev_v is not None and next_v is not None:
            if data[i] < prev_v and data[i] < next_v:
                flags[i] = True
    return pd.Series(flags, index=getattr(series, "index", range(len(flags))))


def double_top(
    df: pd.DataFrame,
    *,
    window: int = 5,
    tolerance: float = 0.03,
) -> pd.Series:
    """Detect double-top patterns.

    A signal is True at the second peak if two local maxima within ``window``
    bars have similar heights (within ``tolerance``).
    """
    highs = df["high"]
    peaks = _local_max(highs)
    result = pd.Series(False, index=df.index)
    last_idx = None
    last_val = None
    for i in range(len(df)):
        if not peaks.iloc[i]:
            continue
        if last_idx is not None and i - last_idx <= window:
            if abs(highs.iloc[i] - last_val) / max(highs.iloc[i], last_val) <= tolerance:
                result.iloc[i] = True
        last_idx = i
        last_val = highs.iloc[i]
    return result


def double_bottom(
    df: pd.DataFrame,
    *,
    window: int = 5,
    tolerance: float = 0.03,
) -> pd.Series:
    """Detect double-bottom patterns using local minima."""
    lows = df["low"]
    troughs = _local_min(lows)
    result = pd.Series(False, index=df.index)
    last_idx = None
    last_val = None
    for i in range(len(df)):
        if not troughs.iloc[i]:
            continue
        if last_idx is not None and i - last_idx <= window:
            if abs(lows.iloc[i] - last_val) / max(lows.iloc[i], last_val) <= tolerance:
                result.iloc[i] = True
        last_idx = i
        last_val = lows.iloc[i]
    return result


# Mapping from pattern name to detector function
PATTERN_FUNCS = {
    "doji": is_doji,
    "double_top": double_top,
    "double_bottom": double_bottom,
}


def scan_all(df: pd.DataFrame, patterns: list[str] | None = None) -> dict[str, pd.Series]:
    """Run all detectors and return a mapping of pattern name to Series."""
    funcs = PATTERN_FUNCS
    if patterns is not None:
        funcs = {k: v for k, v in funcs.items() if k in patterns}
    return {name: func(df) for name, func in funcs.items()}


def get_last_pattern_name(df: pd.DataFrame, patterns: list[str] | None = None) -> str | None:
    """Return the most recently triggered pattern name for ``df``."""
    last_name = None
    last_idx = None
    for name, series in scan_all(df, patterns).items():
        idx_list = [series.index[i] for i, val in enumerate(series) if val]
        if idx_list:
            idx = idx_list[-1]
            if last_idx is None or idx > last_idx:
                last_idx = idx
                last_name = name
    return last_name