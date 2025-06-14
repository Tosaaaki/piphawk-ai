"""Offline training using DQN with PER."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
from d3rlpy.algos import DQN
from d3rlpy.dataset import MDPDataset, PrioritizedReplayBuffer
from d3rlpy.logging import TensorboardLogging
from d3rlpy.metrics.scorer import evaluate_on_environment

from .data_buffer import DataBuffer


def _vec(state: dict[str, Any]) -> list[float]:
    """辞書状態をベクトルへ変換する."""
    return [float(state.get(k, 0.0)) for k in sorted(state.keys())]


def load_dataset(buffer: DataBuffer) -> MDPDataset | None:
    """バッファから MDPDataset を構築する."""
    data = list(buffer.fetch_all())
    if not data:
        return None
    observations = np.array([_vec(s) for s, _, _ in data], dtype=np.float32)
    actions = np.array([a for _, a, _ in data], dtype=np.int64)
    rewards = np.array([r for _, _, r in data], dtype=np.float32)
    terminals = np.zeros(len(data), dtype=np.float32)
    return MDPDataset(observations, actions, rewards, terminals)


def train(buffer: DataBuffer, outdir: Path) -> None:
    """DQN+PER で 50 epoch 学習する."""
    dataset = load_dataset(buffer)
    if dataset is None:
        print("no data")
        return
    outdir.mkdir(parents=True, exist_ok=True)
    algo = DQN(use_gpu=False, replay_buffer_factory=PrioritizedReplayBuffer)
    logger = TensorboardLogging(str(outdir / "tb"))
    algo.fit(dataset, n_epochs=50, logdir=str(outdir), logger=logger)
    algo.save_model(str(outdir / "model.d3"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--redis-url", type=str, default=None)
    p.add_argument("--pg-dsn", type=str, default=None)
    p.add_argument("--outdir", type=Path, default=Path("models/rl"))
    args = p.parse_args()
    buf = DataBuffer(redis_url=args.redis_url, pg_dsn=args.pg_dsn)
    train(buf, args.outdir)


if __name__ == "__main__":
    main()
