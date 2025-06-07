"""RL ポリシーに基づく戦略セレクタ."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "strategy_policy.pkl"

class PolicyBasedSelector:
    def __init__(self, strategies: Sequence[str]):
        self.strategies = list(strategies)
        self.policy = None
        if MODEL_PATH.exists():
            self._load_model()

    def _load_model(self) -> None:
        import pickle
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        actions = data.get("actions", [])
        q_table = data.get("q", {})
        self.actions = actions
        self.q_table = {k: np.array(v) for k, v in q_table.items()}

    def select(self, state: dict[str, Any]) -> str:
        key = json.dumps(state)
        if hasattr(self, "q_table") and key in self.q_table:
            idx = int(np.argmax(self.q_table[key]))
            return self.actions[idx]
        return self.strategies[0] if self.strategies else ""

__all__ = ["PolicyBasedSelector"]
