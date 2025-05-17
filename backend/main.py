from __future__ import annotations

"""Convenience entry point for running Piphawk components."""

import argparse

from backend.utils import env_loader

import uvicorn

from backend.scheduler.job_runner import JobRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Piphawk components")
    parser.add_argument(
        "component",
        choices=["api", "job"],
        help="Component to run: 'api' starts the FastAPI server, 'job' runs the job scheduler",
    )
    args = parser.parse_args()

    if args.component == "api":
        port = int(env_loader.get_env("API_PORT", "8080"))
        uvicorn.run("backend.api.main:app", host="0.0.0.0", port=port)
    else:
        runner = JobRunner()
        runner.run()


if __name__ == "__main__":
    main()
