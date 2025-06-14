"""RL学習用のデータバッファ."""

from __future__ import annotations

import json
from typing import Any, Iterable, Tuple


class DataBuffer:
    """RedisまたはPostgreSQLへ遷移を保存する簡易バッファ."""

    def __init__(self, redis_url: str | None = None, pg_dsn: str | None = None) -> None:
        self.backend = "memory"
        self._data: list[Tuple[dict[str, Any], int, float]] = []
        if redis_url:
            import redis  # type: ignore

            self.backend = "redis"
            self._redis = redis.Redis.from_url(redis_url)
        elif pg_dsn:
            import psycopg2  # type: ignore
            from psycopg2.extras import Json

            self.backend = "pg"
            self._pg = psycopg2.connect(pg_dsn)
            with self._pg.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rl_buffer (
                        id SERIAL PRIMARY KEY,
                        state JSONB,
                        action INTEGER,
                        reward FLOAT
                    )
                    """
                )
                self._pg.commit()

    def append(self, state: dict[str, Any], action: int, reward: float) -> None:
        """状態・行動・報酬をバッファへ追加する."""
        if self.backend == "redis":
            self._redis.rpush(
                "rl_buffer", json.dumps({"state": state, "action": action, "reward": reward})
            )
        elif self.backend == "pg":
            from psycopg2.extras import Json  # type: ignore

            with self._pg.cursor() as cur:
                cur.execute(
                    "INSERT INTO rl_buffer (state, action, reward) VALUES (%s, %s, %s)",
                    (Json(state), action, reward),
                )
                self._pg.commit()
        else:
            self._data.append((state, action, reward))

    def fetch_all(self) -> Iterable[Tuple[dict[str, Any], int, float]]:
        """すべての遷移を返す."""
        if self.backend == "redis":
            items = self._redis.lrange("rl_buffer", 0, -1)
            for item in items:
                data = json.loads(item)
                yield data["state"], data["action"], float(data["reward"])
        elif self.backend == "pg":
            with self._pg.cursor() as cur:
                cur.execute("SELECT state, action, reward FROM rl_buffer")
                for state, action, reward in cur.fetchall():
                    yield state, int(action), float(reward)
        else:
            yield from self._data


__all__ = ["DataBuffer"]
