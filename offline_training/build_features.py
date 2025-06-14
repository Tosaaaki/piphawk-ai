from __future__ import annotations

"""candles parquetから特徴量テーブルを生成する."""

import argparse
from pathlib import Path

import pandas as pd

from indicators.ema import add_ema
from indicators.macd import calc_macd
from indicators.rsi import calc_rsi


def build_feature_table(candle_path: str) -> pd.DataFrame:
    df = pd.read_parquet(candle_path).sort_values("time")
    df = add_ema(df, [21, 55, 200])
    df["RSI"] = calc_rsi(df["close"], period=14)
    macd, signal = calc_macd(df["close"])
    df["MACD"], df["MACD_signal"] = macd, signal
    df = df.dropna().reset_index(drop=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    feats = build_feature_table(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    feats.to_feather(out_path)
    print(f"\u2705 Features saved: {out_path} ({len(feats):,} rows)")


if __name__ == "__main__":
    main()
