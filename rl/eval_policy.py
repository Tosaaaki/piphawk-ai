"""Evaluate trained policy by virtual trading."""

from __future__ import annotations

import argparse

import pandas as pd
from d3rlpy.algos import DQN

from pipelines.walk_forward.utils import calc_sharpe, simulate_trades


def run(model_path: str, csv_path: str, baseline: float) -> dict:
    """3ヶ月の仮想売買を行い指標を計算する."""
    df = pd.read_csv(csv_path)
    model = DQN().load_model(model_path)
    returns = simulate_trades(model, df)
    sharpe = calc_sharpe(returns)
    return {"sharpe": sharpe, "ok": sharpe > baseline}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--data", default="tests/data/range_sample.csv")
    p.add_argument("--baseline", type=float, default=0.0)
    args = p.parse_args()
    metrics = run(args.model, args.data, args.baseline)
    print(metrics)


if __name__ == "__main__":
    main()
