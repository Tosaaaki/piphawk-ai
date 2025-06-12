from __future__ import annotations

"""Tick-based metric calculations."""

from typing import Iterable

from backend.utils import env_loader


def calc_of_imbalance(ticks: Iterable[dict]) -> float:
    """Return order flow imbalance from tick sequence."""
    up = down = 0
    last_mid = None
    for t in ticks:
        try:
            bid = float(t.get("bid") or t["bids"][0]["price"])
            ask = float(t.get("ask") or t["asks"][0]["price"])
        except Exception:
            continue
        mid = (bid + ask) / 2
        if last_mid is not None:
            if mid > last_mid:
                up += 1
            elif mid < last_mid:
                down += 1
        last_mid = mid
    total = up + down
    if total == 0:
        return 0.0
    return (up - down) / total


def calc_vol_burst(ticks: Iterable[dict]) -> float:
    """Return volume burst ratio of latest tick to previous average."""
    volumes: list[float] = []
    for t in ticks:
        v = t.get("volume") or t.get("v")
        if v is not None:
            try:
                volumes.append(float(v))
            except Exception:
                continue
    if len(volumes) < 2:
        return 0.0
    last = volumes[-1]
    avg = sum(volumes[:-1]) / (len(volumes) - 1)
    return last / avg if avg else 0.0


def calc_spd_avg(ticks: Iterable[dict]) -> float:
    """Return average spread in pips."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    spreads = []
    for t in ticks:
        try:
            bid = float(t.get("bid") or t["bids"][0]["price"])
            ask = float(t.get("ask") or t["asks"][0]["price"])
        except Exception:
            continue
        spreads.append(ask - bid)
    if not spreads:
        return 0.0
    return sum(spreads) / len(spreads) / pip_size


def calc_tick_features(ticks: Iterable[dict]) -> dict:
    """Return tick feature dictionary used for micro scalping."""
    return {
        "of_imbalance": calc_of_imbalance(ticks),
        "vol_burst": calc_vol_burst(ticks),
        "spd_avg": calc_spd_avg(ticks),
    }


__all__ = [
    "calc_of_imbalance",
    "calc_vol_burst",
    "calc_spd_avg",
    "calc_tick_features",
]
