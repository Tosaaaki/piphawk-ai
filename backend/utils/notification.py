

"""
Utility module for outbound LINE notifications.

Put *all* LINE‑messaging logic here so that other modules
(api.main, scheduler.job_runner, etc.) can simply:

    from backend.utils.notification import send_line_message
"""

import logging

from fastapi import HTTPException
from linebot import LineBotApi
from linebot.models import TextSendMessage

from backend.utils import env_loader

logger = logging.getLogger(__name__)



def send_line_message(text: str, token: str | None = None, user_id: str | None = None) -> None:
    """
    Send a LINE push message to the configured user.

    Raises
    ------
    HTTPException
        * 500 if the token / user‑ID is not configured
        * 500 if the underlying LINE SDK raises an error
    """
    token = token or env_loader.get_env("LINE_CHANNEL_TOKEN", "")
    user_id = user_id or env_loader.get_env("LINE_USER_ID", "")

    if not token or not user_id:
        raise HTTPException(
            status_code=500,
            detail="LINE API token or user ID not configured",
        )

    try:
        LineBotApi(token).push_message(user_id, TextSendMessage(text=text))
        logger.debug("Sent LINE message: %s", text)
    except Exception as exc:  # noqa: BLE001
        logger.error("LINE API error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def send_range_break_alert(direction: str) -> None:
    """Send a short Range Break notification."""
    send_line_message(f"⚡️Range Break! {direction}")
