#!/usr/bin/env bash
set -euo pipefail

git -C /opt/piphawk pull --ff-only

docker compose -f /opt/piphawk/docker-compose.yml build --pull --platform linux/amd64

docker compose -f /opt/piphawk/docker-compose.yml up -d --force-recreate
