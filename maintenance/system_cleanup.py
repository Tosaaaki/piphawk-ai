#!/usr/bin/env python3
"""System maintenance script"""

import os
import shutil
import subprocess
from argparse import ArgumentParser
from datetime import datetime

# 日本語でログ出力を行うヘルパー

def log(msg: str) -> None:
    print(f"{datetime.now().strftime('%F %T')}  [CLEAN] {msg}")


def run(cmd: str, dry_run: bool = False) -> None:
    """Run shell command ignoring failures.

    If ``sudo`` is not available, drop the prefix and execute the command
    directly. This allows running the script in environments without root
    privileges.
    """
    if dry_run:
        print(f"[DRY RUN] {cmd}")
        return

    if shutil.which("sudo") is None:
        stripped = cmd.lstrip()
        if stripped.startswith("sudo "):
            cmd = stripped[5:]
    try:
        subprocess.run(cmd, check=True, shell=True)
    except FileNotFoundError:
        return
    except subprocess.CalledProcessError:
        pass


def cleanup(dry_run: bool = False) -> None:
    """クリーンアップ処理を実行"""
    # 1) APTキャッシュを削除
    log("Cleaning APT cache ...")
    run("sudo apt-get clean -y", dry_run)

    # 2) 7日より古いジャーナルログを削除
    log("Vacuum old journal logs (≥7d) ...")
    run("sudo journalctl --vacuum-time=7d", dry_run)

    # 3) Dockerの不要リソースを削除
    if shutil.which("docker"):
        log("Pruning Docker images/containers/volumes ...")
        run("sudo docker system prune -af --volumes", dry_run)

    # 4) pip関連キャッシュを削除
    log("Removing pip cache ...")
    run("rm -rf ~/.cache/pip ~/.cache/pypoetry ~/.cache/pypi", dry_run)

    # 5) 1GiB以上のログファイルを空にする
    log("Truncating huge /var/log files (≥1GiB) ...")
    for root, _dirs, files in os.walk("/var/log"):
        for name in files:
            path = os.path.join(root, name)
            try:
                if os.path.getsize(path) >= 1024 * 1024 * 1024:
                    log(f"  -> truncating {path}")
                    run(f"sudo truncate -s 0 {path}", dry_run)
            except FileNotFoundError:
                continue

    # 6) /tmp配下の30日以上前のファイルを削除
    log("Cleaning old /tmp files ...")
    run("sudo find /tmp -type f -mtime +30 -delete", dry_run)

    # 7) 最終的なディスク使用量を表示
    log("Done.  Disk usage after cleanup:")
    run("df -h /", dry_run)


def main(dry_run: bool = False, ask_confirmation: bool = True) -> None:
    """オプションに応じてクリーンアップを実行"""
    if ask_confirmation:
        reply = input("Proceed with system cleanup? [y/N] ").strip().lower()
        if reply not in {"y", "yes"}:
            print("Aborted.")
            return
    cleanup(dry_run)


if __name__ == "__main__":
    parser = ArgumentParser(description="System maintenance script")
    parser.add_argument("--dry-run", action="store_true", help="show commands without executing")
    parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompt")
    args = parser.parse_args()
    main(dry_run=args.dry_run, ask_confirmation=not args.yes)
