#!/usr/bin/env bash
set -euo pipefail
pip install --only-binary=:all: -r requirements-test.txt
pytest "$@"
