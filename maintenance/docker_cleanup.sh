#!/usr/bin/env bash
set -euo pipefail

# しきい値は環境変数 THRESHOLD で指定（デフォルト 80）
THRESHOLD="${THRESHOLD:-80}"

used=$(df --output=pcent / | tail -1 | tr -dc '0-9')

if [ "$used" -ge "$THRESHOLD" ]; then
  echo "[docker-cleanup] rootfs ${used}% \u2265 ${THRESHOLD}%. Cleaning…" | logger

  docker image prune -a -f
  docker builder prune -af
  rm -rf "$HOME/.vscode-server/bin/"*

  new_used=$(df --output=pcent / | tail -1 | tr -dc '0-9')
  echo "[docker-cleanup] Done. (${used}% \u2794 ${new_used}%)" | logger
fi
