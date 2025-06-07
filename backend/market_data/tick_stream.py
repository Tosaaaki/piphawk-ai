from __future__ import annotations

"""OANDA streaming client via HTTP long polling."""

import json
from typing import Iterable, Callable

import requests
from backend.utils import env_loader

STREAM_URL = env_loader.get_env("OANDA_STREAM_URL", "https://stream-fxtrade.oanda.com/v3")
ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
API_KEY = env_loader.get_env("OANDA_API_KEY")


def start_stream(pairs: Iterable[str], callback: Callable[[dict], None]) -> None:
    """指定ペアのストリームを開始し、各ティックをコールバックへ渡す."""
    url = f"{STREAM_URL}/accounts/{ACCOUNT_ID}/pricing/stream"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"instruments": ",".join(pairs)}
    with requests.Session() as session:
        with session.get(url, headers=headers, params=params, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                callback(data)
