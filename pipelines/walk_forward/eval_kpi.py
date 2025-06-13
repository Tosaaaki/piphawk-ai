"""Evaluate KPI and decide retrain flag."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_json(args.infile)
    mean_bt = df["bt_sharpe"].mean()
    mean_fwd = df["fwd_sharpe"].mean()

    retrain = mean_fwd > 1.2 and mean_fwd > mean_bt
    Path("retrain_flag.txt").write_text("true" if retrain else "false")


if __name__ == "__main__":
    main()
