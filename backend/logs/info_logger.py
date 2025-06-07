import logging

# INFOログ用ユーティリティ
logger = logging.getLogger(__name__)


def info(key: str, **vals) -> None:
    """Log formatted INFO message.

    Parameters
    ----------
    key : str
        イベント種別を表すキー
    **vals : Any
        付加情報をキー=値形式で受け取る
    """
    msg = " ".join(f"{k}={v}" for k, v in vals.items())
    logger.info("%s %s", key, msg)

__all__ = ["logger", "info"]
