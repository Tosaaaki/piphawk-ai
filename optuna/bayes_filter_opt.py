from __future__ import annotations

"""Bayesian optimization for entry filter parameters."""

import json
import os
import subprocess
from pathlib import Path

import yaml

import optuna

DATA_PATH = Path("training/examples/sample_rates.csv")
MODEL_PATH = Path("models/sample_model.pkl")


def objective(trial: optuna.Trial) -> float:
    """Run backtest CLI with trial parameters and return Sharpe ratio."""
    params = {
        "MIN_VOL_MA": trial.suggest_int("MIN_VOL_MA", 40, 120),
        "VOL_MA_PERIOD": trial.suggest_int("VOL_MA_PERIOD", 3, 10),
        "CNN_PROB_THRESHOLD": trial.suggest_float("CNN_PROB_THRESHOLD", 0.55, 0.85),
    }
    env = os.environ.copy()
    env.update({k: str(v) for k, v in params.items()})
    subprocess.run(
        [
            "python",
            "offline_training/backtest.py",
            "--model",
            str(MODEL_PATH),
            "--data",
            str(DATA_PATH),
            "--out",
            "metrics.json",
        ],
        check=True,
        env=env,
    )
    with open("metrics.json") as f:
        metrics = json.load(f)
    return float(metrics.get("sharpe", 0))


def main() -> None:
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=24)
    with open("best_filters.yaml", "w") as f:
        yaml.safe_dump(study.best_params, f, sort_keys=False)


if __name__ == "__main__":
    main()
