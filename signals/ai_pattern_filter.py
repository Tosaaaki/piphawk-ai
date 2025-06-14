from __future__ import annotations

"""AI-based pattern filter using CNN."""

from io import BytesIO
from typing import Iterable, Mapping

import matplotlib.pyplot as plt
import numpy as np

from ai.cnn_pattern import infer


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
    res = infer.predict(img)
    prob = res.get("pattern", 0.0)
    return prob > 0.65, prob


__all__ = ["pass_pattern_filter"]
