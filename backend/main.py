from __future__ import annotations

"""Convenience entry point for running Piphawk components."""

import argparse
import logging

import uvicorn

from backend.logs.log_manager import init_db
from backend.scheduler.job_runner import JobRunner
from backend.utils import env_loader


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Piphawk components")
    parser.add_argument(
        "component",
        choices=["api", "job"],
        help="Component to run: 'api' starts the FastAPI server, 'job' runs the job scheduler",
    )
    args = parser.parse_args()

    # DBが初期化されていない場合はここで作成しておく
    try:
        init_db()
    except Exception as exc:  # pragma: no cover - 初期化失敗はログ出力のみに留める
        logging.getLogger(__name__).warning("init_db failed: %s", exc)

    if args.component == "api":
        port = int(env_loader.get_env("API_PORT", "8080"))
        uvicorn.run("backend.api.main:app", host="0.0.0.0", port=port)
    else:
        if env_loader.get_env("QUICK_TP_MODE", "false").lower() == "true":
            from execution.quick_tp_mode import run_loop

            run_loop()
        else:
            runner = JobRunner()
            runner.run()


if __name__ == "__main__":
    main()
