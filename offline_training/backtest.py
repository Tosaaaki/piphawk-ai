from __future__ import annotations

"""Simple walk-forward backtest."""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from pipelines.walk_forward.utils import calc_sharpe, simulate_trades


def run(model_path: str, dataset_path: str) -> dict:
    model = joblib.load(model_path)
    df = pd.read_feather(dataset_path)
    returns = simulate_trades(model, df)
    sharpe = calc_sharpe(returns)
    win_rate = float(np.mean(returns > 0)) if len(returns) else 0.0
    max_dd = float(np.min(np.cumsum(returns)))
    metrics = {"sharpe": sharpe, "win_rate": win_rate, "max_dd": max_dd}
    return metrics


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--out", type=Path, default=Path("metrics.json"))
    args = p.parse_args()
    metrics = run(args.model, args.data)
    args.out.write_text(pd.Series(metrics).to_json())
    print(metrics)


if __name__ == "__main__":
    main()
