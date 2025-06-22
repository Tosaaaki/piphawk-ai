"""Offline RL trainer for strategy selection."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

import numpy as np
from d3rlpy.algos import DiscreteCQL
from d3rlpy.dataset import MDPDataset

from backend.utils import db_helper, env_loader

DB_PATH = Path(env_loader.get_env("TRADES_DB_PATH", db_helper.DB_PATH))
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "policy_model.d3"


def _vec(state: Dict[str, Any]) -> list[float]:
    """Convert state dict to numeric vector."""
    return [float(state.get(k, 0.0)) for k in sorted(state.keys())]


def load_dataset(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT state, action, reward FROM policy_transitions")
    rows = cur.fetchall()
    if not rows:
        return None, None
    observations = []
    actions = []
    rewards = []
    for s_json, action, reward in rows:
        state = json.loads(s_json)
        observations.append(_vec(state))
        actions.append(action)
        rewards.append(float(reward))
    arm_index = {a: i for i, a in enumerate(sorted(set(actions)))}
    action_idxs = [arm_index[a] for a in actions]
    dataset = MDPDataset(
        observations=np.array(observations, dtype=np.float32),
        actions=np.array(action_idxs, dtype=np.int64),
        rewards=np.array(rewards, dtype=np.float32),
        terminals=np.zeros(len(observations), dtype=np.float32),
    )
    return dataset, arm_index


def train() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        dataset, arm_index = load_dataset(conn)
    if dataset is None:
        print("No data found for training")
        return
    algo = DiscreteCQL(use_gpu=False)
    algo.fit(dataset, n_epochs=5, verbose=False)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    algo.save(str(MODEL_PATH))
    with open(MODEL_PATH.with_suffix(".json"), "w") as f:
        json.dump({"actions": arm_index}, f)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
