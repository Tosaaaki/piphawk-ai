from __future__ import annotations

"""LogisticRegressionを用いて説明算のトレーニング."""

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


def train(dataset_path: str, model_dir: str) -> dict:
    df = pd.read_feather(dataset_path)
    X = df.drop(columns=["label", "time"])
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = float(accuracy_score(y_test, preds))

    Path(model_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(model, Path(model_dir) / "model.pkl")
    metrics = {"accuracy": acc}
    Path(model_dir).joinpath("metrics.json").write_text(pd.Series(metrics).to_json())
    return metrics


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--outdir", required=True)
    args = p.parse_args()
    metrics = train(args.data, args.outdir)
    print(metrics)


if __name__ == "__main__":
    main()
