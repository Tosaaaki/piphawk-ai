from __future__ import annotations

"""OANDA streaming client via HTTP long polling."""

import asyncio
import json
from typing import Callable, Iterable

import httpx
import requests

from backend.utils import env_loader

STREAM_URL = env_loader.get_env("OANDA_STREAM_URL", "https://stream-fxtrade.oanda.com/v3")
ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
API_KEY = env_loader.get_env("OANDA_API_KEY")


def start_stream_sync(pairs: Iterable[str], callback: Callable[[dict], None]) -> None:
    """同期版ストリーム取得."""
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


async def start_stream(pairs: Iterable[str], callback: Callable[[dict], None]) -> None:
    """非同期にティックストリームを取得し、切断時は指数バックオフで再接続する."""
    url = f"{STREAM_URL}/accounts/{ACCOUNT_ID}/pricing/stream"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {"instruments": ",".join(pairs)}
    backoff = 1
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, headers=headers, params=params) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        callback(data)
            backoff = 1
        except Exception:
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
