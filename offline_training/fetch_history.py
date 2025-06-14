from __future__ import annotations

"""OANDAの古いローソク買いデータを下げるスクリプト."""

import argparse
import datetime as dt
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests

OANDA_API_URL = os.environ.get("OANDA_API_URL", "https://api-fxtrade.oanda.com")
OANDA_API_KEY = os.environ.get("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID")
INSTRUMENT = os.environ.get("OANDA_INSTRUMENT", "EUR_USD")
GRANULARITY = os.environ.get("OANDA_GRANULARITY", "M5")


def fetch_candles(start: dt.datetime, end: dt.datetime) -> pd.DataFrame:
    """指定区間のローソク買いデータを取得する."""
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params: dict[str, Any] = {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "granularity": GRANULARITY,
        "price": "M",
    }
    url = f"{OANDA_API_URL}/v3/instruments/{INSTRUMENT}/candles"
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("candles", [])
    if not data:
        return pd.DataFrame()
    rows = [
        {
            "time": c["time"],
            "open": float(c["mid"]["o"]),
            "high": float(c["mid"]["h"]),
            "low": float(c["mid"]["l"]),
            "close": float(c["mid"]["c"]),
            "volume": int(c["volume"]),
        }
        for c in data
    ]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("parquet"))
    args = parser.parse_args()

    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=args.days)
    df = fetch_candles(start, end)
    if df.empty:
        print("No data fetched")
        return
    args.output.mkdir(parents=True, exist_ok=True)
    fname = args.output / f"candles_{start.date()}_{end.date()}.parquet"
    df.to_parquet(fname)
    print(f"Saved {len(df)} rows to {fname}")


if __name__ == "__main__":
    main()
