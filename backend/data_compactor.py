"""Helpers to compress trading state for OpenAI prompts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.utils.prompt_loader import load_template

# 指標の抽出キーと短縮名
_KEY_MAP = {
    "ema12_15m": "e12",
    "ema26_15m": "e26",
    "ema_slope_15m": "es",
    "stddev_pct_15m": "sd",
    "adx_15m": "adx",
    "atr_15m": "atr",
    "overshoot_flag": "over",
    "range_ratio": "rng",
}

_last_hash: int | None = None
_sys_cache: Dict[str, Any] | None = None


def _load_sys() -> Dict[str, str]:
    """Load system prompt once and cache."""
    global _sys_cache
    if _sys_cache is None:
        text = load_template("entry_system.txt")
        _sys_cache = {"role": "system", "content": text}
    return _sys_cache  # type: ignore[return-value]


def _format_bar(bar: Dict[str, Any]) -> List[float]:
    """Return [o,h,l,c,v] rounded to 2 decimals."""
    return [
        round(float(bar.get("o") or bar.get("open") or 0), 2),
        round(float(bar.get("h") or bar.get("high") or 0), 2),
        round(float(bar.get("l") or bar.get("low") or 0), 2),
        round(float(bar.get("c") or bar.get("close") or 0), 2),
        round(float(bar.get("v") or bar.get("volume") or 0), 2),
    ]


def compact_state(
    bars: List[Dict[str, Any]], indicators: Dict[str, Any], position: Dict[str, Any] | None
) -> Dict[str, Any]:
    """Return Compact State v1 JSON object."""
    comp_bars = [_format_bar(b) for b in bars[-30:]]
    comp_ind = {}
    for k, short in _KEY_MAP.items():
        val = indicators.get(k)
        if hasattr(val, "iloc"):
            val = val.iloc[-1] if len(val) else 0.0
        elif isinstance(val, (list, tuple)):
            val = val[-1] if val else 0.0
        if isinstance(val, (int, float)):
            comp_ind[short] = round(float(val), 3)
        else:
            comp_ind[short] = bool(val)
    pos_str = ""
    if position:
        units = position.get("units", 0)
        avg = float(position.get("average_price", 0))
        pl = float(position.get("unrealizedPL", 0))
        pos_str = f"{units}@{avg:.2f} pl={pl:.1f}"
    return {
        "bars": comp_bars,
        "ind": comp_ind,
        "pos": pos_str,
        "clk": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def build_messages(
    bars: List[Dict[str, Any]], indicators: Dict[str, Any], position: Dict[str, Any] | None
) -> List[Dict[str, str]]:
    """Return chat messages using diff suppression."""
    global _last_hash
    ctx = compact_state(bars, indicators, position)
    content = json.dumps(ctx, separators=(",", ":"))
    h = hash(content)
    if h == _last_hash:
        user_msg = {"role": "user", "content": "{\"noop\":true}"}
    else:
        _last_hash = h
        user_msg = {"role": "user", "content": content}
    return [_load_sys(), user_msg]


__all__ = ["compact_state", "build_messages"]
