"""簡易リスクフィルタ集."""
from __future__ import annotations

import time

_last = {"side": None, "time": 0.0}


def spread_ok(spread: float, atr: float | None) -> bool:
    """スプレッドが許容範囲か判定."""
    if atr is None:
        return True
    return spread <= atr * 0.15


def margin_ok(account: dict | None) -> bool:
    """証拠金余裕率をチェック."""
    if not isinstance(account, dict):
        return True
    try:
        avail = float(account.get("marginAvailable", 0))
        nav = float(account.get("NAV", 0))
        if nav <= 0:
            return False
        return avail / nav > 0.05
    except Exception:
        return True


def duplicate_guard(side: str) -> bool:
    """直近取引との重複を避ける."""
    now = time.time()
    if _last["side"] == side and now - _last["time"] < 30:
        return False
    _last["side"] = side
    _last["time"] = now
    return True


def check_all(spread: float, atr: float | None, account: dict | None, side: str) -> bool:
    if not spread_ok(spread, atr):
        return False
    if not margin_ok(account):
        return False
    if not duplicate_guard(side):
        return False
    return True


__all__ = ["check_all"]
