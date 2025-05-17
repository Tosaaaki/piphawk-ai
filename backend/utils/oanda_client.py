"""
OANDA helper – pending LIMIT order lookup
----------------------------------------

Exposes exactly one public function:

    get_pending_entry_order(instrument: str) -> dict | None

It searches the logged‑in account for *PENDING* LIMIT orders on the given
instrument that we created (identified by {"mode":"limit","entry_uuid":...}
inside clientExtensions.comment).

If such an order exists, it returns::

    {"order_id": "12345", "ts": 1715920000}

where *ts* is the UNIX timestamp stored in clientExtensions.tag.  
If no order is found – or an HTTP error occurs – it returns *None*.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional
from backend.utils import env_loader

import requests
from requests.exceptions import HTTPError, RequestException

# ──────────────────────────────────
#   Environment / Constants
# ──────────────────────────────────
OANDA_API_URL = env_loader.get_env("OANDA_API_URL", "https://api-fxtrade.oanda.com/v3")
OANDA_ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
OANDA_API_KEY = env_loader.get_env("OANDA_API_KEY")

if not (OANDA_ACCOUNT_ID and OANDA_API_KEY):
    raise EnvironmentError("OANDA_ACCOUNT_ID / OANDA_API_KEY not configured")

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json",
}

# ──────────────────────────────────
#   Lightweight in‑memory cache
# ──────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SEC = 8  # we call this inside ~60‑s main loop

# ----------------------------------------------------------------------
def _fetch_pending_orders(instrument: str) -> list[dict]:
    """Raw GET for pending orders on *instrument*."""
    url = (
        f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}"
        f"/orders?state=PENDING&instrument={instrument}"
    )
    response = requests.get(url, headers=HEADERS, timeout=5)
    response.raise_for_status()
    return response.json().get("orders", [])


def get_pending_entry_order(instrument: str) -> Optional[dict]:
    """
    Return dict {order_id, ts} for our own pending LIMIT entry order, or None.

    Detection rule:
      • order.type == "LIMIT"
      • JSON(clientExtensions.comment) has keys {"mode":"limit","entry_uuid":...}
    """
    now = time.time()
    cached = _cache.get(instrument)
    if cached and now - cached["fetched_at"] < _CACHE_TTL_SEC:
        return cached["result"]

    try:
        orders = _fetch_pending_orders(instrument)
    except (HTTPError, RequestException) as exc:
        print(f"[oanda_client] HTTP error when fetching orders: {exc}")
        _cache[instrument] = {"fetched_at": now, "result": None}
        return None

    result: Optional[dict] = None
    for order in orders:
        if order.get("type") != "LIMIT":
            continue

        comment_text = order.get("clientExtensions", {}).get("comment", "")
        tag_text = order.get("clientExtensions", {}).get("tag", "0")

        try:
            meta = json.loads(comment_text)
        except json.JSONDecodeError:
            continue

        if meta.get("mode") == "limit" and meta.get("entry_uuid"):
            try:
                ts_val = int(tag_text)
            except ValueError:
                ts_val = 0
            result = {"order_id": order["id"], "ts": ts_val}
            break

    _cache[instrument] = {"fetched_at": now, "result": result}
    return result