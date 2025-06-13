import logging

from backend.logs.reconcile_trades import reconcile_trades
from backend.logs.update_oanda_trades import update_oanda_trades

logger = logging.getLogger(__name__)


def sync_exits() -> None:
    """Update trade exits using OANDA history."""
    logger.info("Updating oanda_trades from API")
    try:
        update_oanda_trades()
    except Exception as exc:  # network or auth error
        logger.warning("update_oanda_trades failed: %s", exc)
    logger.info("Reconciling local trades table")
    reconcile_trades()


if __name__ == "__main__":
    sync_exits()
