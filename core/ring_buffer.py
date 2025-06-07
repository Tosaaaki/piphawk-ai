from collections import deque
from typing import Any, Iterable


class RingBuffer:
    """固定長リングバッファ."""

    def __init__(self, maxlen: int) -> None:
        self._buf = deque(maxlen=maxlen)

    def append(self, item: Any) -> None:
        """データを追加する."""
        self._buf.append(item)

    def latest(self, n: int | None = None) -> list[Any]:
        """最新の n 件を取得する."""
        if n is None:
            return [self._buf[-1]] if self._buf else []
        if n <= 0:
            return []
        return list(self._buf)[-n:]

    def __len__(self) -> int:  # pragma: no cover - simple wrapper
        return len(self._buf)
