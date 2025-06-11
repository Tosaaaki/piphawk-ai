import asyncio
from typing import Any, Coroutine, TypeVar


T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """非同期関数を同期的に実行するユーティリティ"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        new_loop = asyncio.new_event_loop()
        try:
            task = new_loop.create_task(coro)
            return new_loop.run_until_complete(task)
        finally:
            new_loop.close()
