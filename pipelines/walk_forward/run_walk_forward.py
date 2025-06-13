"""Walk-forward optimization main script."""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import calc_sharpe, simulate_trades, train_simple_model


def train_model(df: pd.DataFrame):
    """Fit a simple logistic regression model."""
    return train_simple_model(df)


def run_backtest(model, df: pd.DataFrame):
    """Simulate trading on the training data."""
    returns = simulate_trades(model, df)
    return {"returns": returns}


def run_forward(model, df: pd.DataFrame):
    """Simulate trading on the forward data."""
    returns = simulate_trades(model, df)
    return {"returns": returns}


def evaluate_metrics(bt_result, fwd_result) -> dict:
    """Calculate Sharpe ratio for backtest and forward results."""
    bt_sharpe = calc_sharpe(bt_result["returns"])
    fwd_sharpe = calc_sharpe(fwd_result["returns"])
    return {"bt_sharpe": bt_sharpe, "fwd_sharpe": fwd_sharpe}


def rolling_train_test(ohlc: pd.DataFrame, train_size: int, test_size: int):
    """ジェネレータで訓練区間とテスト区間を返す"""
    for start in range(0, len(ohlc) - train_size - test_size, test_size):
        train = ohlc.iloc[start : start + train_size]
        test = ohlc.iloc[start + train_size : start + train_size + test_size]
        yield train, test


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=Path("models/candidate"))
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    csv_path = Path("tests/data/range_sample.csv")
    ohlc = pd.read_csv(csv_path)
    metrics_all = []
    last_model = None

    for train_df, test_df in rolling_train_test(ohlc, 6, 2):
        last_model = train_model(train_df)
        bt_r = run_backtest(last_model, train_df)
        fwd_r = run_forward(last_model, test_df)
        metrics_all.append(evaluate_metrics(bt_r, fwd_r))

    df_metrics = pd.DataFrame(metrics_all)
    df_metrics.to_json(args.outdir / "metrics.json", orient="records")
    if last_model is not None:
        with open(args.outdir / "model.pkl", "wb") as f:
            pickle.dump(last_model, f)


if __name__ == "__main__":
    main()
