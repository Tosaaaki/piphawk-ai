from __future__ import annotations

"""Utility functions for simple walk-forward trading."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add basic features and target column."""
    df = df.copy()
    df["feat1"] = df["close"] - df["open"]
    df["feat2"] = df["high"] - df["low"]
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df["next_close"] = df["close"].shift(-1)
    return df.dropna().reset_index(drop=True)


def train_simple_model(df: pd.DataFrame):
    """Train logistic regression model. Uses a dummy model if data is degenerate."""
    feats = _prepare_features(df)
    X = feats[["feat1", "feat2"]]
    y = feats["target"]
    if len(np.unique(y)) < 2:
        model = DummyClassifier(strategy="most_frequent")
        model.fit(X, y)
    else:
        model = LogisticRegression()
        model.fit(X, y)
    return model


def simulate_trades(model: LogisticRegression, df: pd.DataFrame) -> np.ndarray:
    """Run prediction and calculate trade returns."""
    feats = _prepare_features(df)
    X = feats[["feat1", "feat2"]]
    preds = model.predict(X)
    pos = preds * 2 - 1
    price_diff = feats["next_close"].values - feats["close"].values
    return pos * price_diff


def calc_sharpe(returns: np.ndarray) -> float:
    """Calculate simple Sharpe ratio."""
    if returns.size == 0:
        return 0.0
    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=1)
    if std_r == 0:
        return 0.0
    return float(mean_r / std_r * np.sqrt(len(returns)))


__all__ = [
    "train_simple_model",
    "simulate_trades",
    "calc_sharpe",
]
