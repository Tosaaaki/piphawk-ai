"""Simple performance logging utility."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "perf_stats.jsonl"


def log_perf(tag: str, start: float, end: float) -> None:
    """Append timing info as JSON line."""
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "tag": tag,
        "elapsed": end - start,
    }
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")
    except Exception:
        pass


class PerfTimer:
    def __init__(self, tag: str):
        self.tag = tag
        self.start = time.perf_counter()

    def stop(self) -> None:
        end = time.perf_counter()
        log_perf(self.tag, self.start, end)


__all__ = ["PerfTimer", "log_perf"]
