"""Apply offline-learned policy to strategy selector."""

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from d3rlpy.algos import DiscreteCQL

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "policy_model.d3"


class OfflinePolicy:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = Path(model_path)
        self.algo: DiscreteCQL | None = None
        self.actions: list[str] = []
        self.load()

    def load(self) -> None:
        if not self.model_path.exists():
            return
        self.algo = DiscreteCQL.from_json(str(self.model_path))
        actions_file = self.model_path.with_suffix(".json")
        if actions_file.exists():
            with open(actions_file) as f:
                data = json.load(f)
            self.actions = [k for k, _ in sorted(data["actions"].items(), key=lambda x: x[1])]

    def _vec(self, context: Dict[str, Any]) -> np.ndarray:
        return np.array([[float(context.get(k, 0.0)) for k in sorted(context.keys())]], dtype=np.float32)

    def select(self, context: Dict[str, Any]) -> str | None:
        if self.algo is None or not self.actions:
            return None
        q_values = self.algo.predict_value(self._vec(context))[0]
        idx = int(np.argmax(q_values))
        if idx < len(self.actions):
            return self.actions[idx]
        return None
