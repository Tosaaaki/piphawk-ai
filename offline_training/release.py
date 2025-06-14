from __future__ import annotations

"""metrics.jsonとthresholdsをチェックしてモデル更新."""

import argparse
import json
import shutil
from pathlib import Path

import yaml

THRESH_PATH = Path("config/thresholds.yml")
MODEL_REPO = Path("models/latest")


def should_release(metrics: dict, thresholds: dict) -> bool:
    return all(metrics.get(k, 0) >= v for k, v in thresholds.items())


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--metrics", required=True)
    p.add_argument("--model", required=True)
    args = p.parse_args()

    thresholds = yaml.safe_load(THRESH_PATH.read_text())
    metrics = json.loads(Path(args.metrics).read_text())
    if should_release(metrics, thresholds):
        MODEL_REPO.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.model, MODEL_REPO / "model.pkl")
        print("\u2705 Model released")
    else:
        print("\u274c Metrics below threshold")


if __name__ == "__main__":
    main()
