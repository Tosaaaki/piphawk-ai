from __future__ import annotations

"""trades.dbから助言を生成し、特徴量データに追加する."""

import argparse
from pathlib import Path

import pandas as pd

from backend.utils.db_helper import connect


def attach_labels(feature_path: str, db_path: str) -> pd.DataFrame:
    df = pd.read_feather(feature_path)
    with connect(db_path) as conn:
        trades = pd.read_sql_query(
            "SELECT entry_time, profit_loss FROM trades WHERE profit_loss IS NOT NULL",
            conn,
        )
    trades["timestamp"] = pd.to_datetime(trades["entry_time"])
    trades["label"] = (trades["profit_loss"] > 0).astype(int)
    merged = pd.merge_asof(
        df.sort_values("time"),
        trades.sort_values("timestamp"),
        left_on="time",
        right_on="timestamp",
        direction="backward",
    )
    merged = merged.drop(columns=["entry_time", "timestamp", "profit_loss"])
    return merged.dropna(subset=["label"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--db", type=str, default="trades.db")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    labeled = attach_labels(args.features, args.db)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    labeled.to_feather(out_path)
    print(f"\u2705 Dataset saved: {out_path} ({len(labeled):,} rows)")


if __name__ == "__main__":
    main()
