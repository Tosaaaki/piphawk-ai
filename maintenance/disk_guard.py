"""Call this from your main loop (or run standalone).
If '/' usage >= 80 %, execute system_cleanup.run()."""
import logging
import shutil

import maintenance.system_cleanup as sc
from backend.utils import env_loader

THRESHOLD = int(env_loader.get_env("CLEANUP_THRESHOLD", "80"))  # %

if not 1 <= THRESHOLD <= 100:
    raise ValueError("CLEANUP_THRESHOLD must be between 1 and 100")

# ルートFS使用率を返す

def root_usage_pct() -> int:
    total, used, _ = shutil.disk_usage("/")
    return used * 100 // total

# 必要ならクリーンアップを実行

def maybe_cleanup() -> int:
    pct = root_usage_pct()
    logging.info("root-fs usage = %s%% (threshold %s%%)", pct, THRESHOLD)
    if pct >= THRESHOLD:
        logging.warning("Disk almost full \u2013 running cleanup ...")
        sc.main(ask_confirmation=False)
        logging.info("Cleanup finished (%s%% \u2794 %s%%)", pct, root_usage_pct())
    return pct

if __name__ == "__main__":
    maybe_cleanup()
