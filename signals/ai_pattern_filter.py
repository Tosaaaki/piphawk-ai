from __future__ import annotations

"""AI-based pattern filter using CNN."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Iterable, Mapping

import matplotlib.pyplot as plt
import numpy as np

from ai.cnn_pattern import infer
from backend.utils import env_loader
from monitoring import prom_exporter as pe

logger = logging.getLogger(__name__)


def _candles_to_image(candles: Iterable[Mapping]) -> np.ndarray:
    ohlc = []
    for i, row in enumerate(candles):
        base = row.get("mid") if isinstance(row.get("mid"), Mapping) else row
        ohlc.append((i, base.get("o"), base.get("h"), base.get("l"), base.get("c")))
    fig, ax = plt.subplots(figsize=(1.28, 1.28), dpi=100)
    ax.axis("off")
    for x, o, h, l, c in ohlc:
        color = "green" if c >= o else "red"
        ax.plot([x, x], [l, h], color=color, linewidth=1)
        ax.add_patch(plt.Rectangle((x - 0.3, min(o, c)), 0.6, abs(o - c), color=color))
    buf = BytesIO()
    fig.canvas.print_png(buf)
    plt.close(fig)
    buf.seek(0)
    img = plt.imread(buf)
    return (img[:, :, :3] * 255).astype(np.uint8)


def pass_pattern_filter(candles: Iterable[Mapping]) -> tuple[bool, float]:
    """Return ``(True, prob)`` when CNN predicts chart pattern."""
    img = _candles_to_image(candles)

    allow_fb = env_loader.get_env("ALLOW_FALLBACK_PATTERN", "no").lower() == "yes"
    model_path = getattr(infer, "_MODEL_PATH", None)
    if model_path and not Path(model_path).exists():
        pe.increment_pattern_model_missing()
        msg = f"CNN weight missing: {model_path}"
        if allow_fb:
            logger.warning(msg)
        else:
            logger.error(msg)
            return False, 0.0

    res = infer.predict(img)
    prob = res.get("pattern", 0.0)
    return prob > 0.65, prob


__all__ = ["pass_pattern_filter"]
