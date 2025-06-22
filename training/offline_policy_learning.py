"""簡易 Q 学習を用いたオフラインポリシー学習スクリプト."""

import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.utils import db_helper, env_loader

DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", db_helper.DB_PATH))
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "strategy_policy.pkl"

class SimpleQ:
    def __init__(self, actions: list[str]):
        self.actions = actions
        self.q: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(len(actions)))

    def update(self, state: str, action: str, reward: float, lr: float = 0.1) -> None:
        idx = self.actions.index(action)
        q_val = self.q[state][idx]
        self.q[state][idx] = q_val + lr * (reward - q_val)

    def fit(self, data: list[tuple[str, str, float]], epochs: int = 5) -> None:
        for _ in range(epochs):
            for s, a, r in data:
                self.update(s, a, r)

    def predict(self, state: str) -> str | None:
        if state not in self.q:
            return None
        return self.actions[int(np.argmax(self.q[state]))]

    def save(self, path: Path) -> None:
        import pickle
        path.parent.mkdir(exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"actions": self.actions, "q": dict(self.q)}, f)


def load_transitions(conn: sqlite3.Connection) -> list[tuple[str, str, float]]:
    cur = conn.cursor()
    cur.execute("SELECT state, action, reward FROM policy_transitions")
    rows = cur.fetchall()
    data = []
    for state, action, reward in rows:
        data.append((state, action, float(reward)))
    return data


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        data = load_transitions(conn)
    if not data:
        print("No data found for training")
        return
    actions = sorted({a for _, a, _ in data})
    agent = SimpleQ(actions)
    agent.fit(data, epochs=10)
    agent.save(MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
