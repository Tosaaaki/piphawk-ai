from __future__ import annotations

"""CNN pattern detection inference utilities."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .model import PatternCNN

_MODEL_PATH = Path(__file__).resolve().parent / "export" / "pattern_cnn_v1.pt"
_model: PatternCNN | None = None


def _load_model() -> PatternCNN:
    global _model
    if _model is None:
        m = PatternCNN()
        try:
            state = torch.load(_MODEL_PATH, map_location="cpu")
            m.load_state_dict(state)
        except Exception:  # pragma: no cover - missing weight case
            pass
        m.eval()
        _model = m
    return _model


def _preprocess(img_np: np.ndarray) -> torch.Tensor:
    img = Image.fromarray(img_np).convert("L").resize((128, 128))
    arr = np.array(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0)
    return tensor


def predict(img_np: np.ndarray) -> dict[str, float]:
    """Return pattern probability given an image array."""
    model = _load_model()
    with torch.no_grad():
        x = _preprocess(img_np)
        prob = float(model(x).item())
    return {"pattern": prob}


__all__ = ["predict"]
