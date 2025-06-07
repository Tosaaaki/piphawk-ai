"""Walk-forward optimization main script."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# TODO: replace these stubs with real implementations

def train_model(df: pd.DataFrame):
    return {}

def run_backtest(model, df: pd.DataFrame):
    return {}

def run_forward(model, df: pd.DataFrame):
    return {}

def evaluate_metrics(bt_result, fwd_result) -> dict:
    return {"bt_sharpe": 1.0, "fwd_sharpe": 1.0}


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

    ohlc = pd.DataFrame()
    metrics_all = []

    for train_df, test_df in rolling_train_test(ohlc, 100, 20):
        model = train_model(train_df)
        bt_r = run_backtest(model, train_df)
        fwd_r = run_forward(model, test_df)
        metrics_all.append(evaluate_metrics(bt_r, fwd_r))

    df_metrics = pd.DataFrame(metrics_all)
    df_metrics.to_json(args.outdir / "metrics.json", orient="records")
    # モデルを保存
    (args.outdir / "model.pkl").write_bytes(b"model")


if __name__ == "__main__":
    main()
