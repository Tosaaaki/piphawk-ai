#!/usr/bin/env bash
# systemdタイマーを自動設定するスクリプト
set -euo pipefail

if command -v sudo >/dev/null; then
  SUDO=sudo
else
  SUDO=""
fi

$SUDO cp maintenance/system_cleanup.service /etc/systemd/system/
$SUDO cp maintenance/system_cleanup.timer /etc/systemd/system/
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now system_cleanup.timer
