

"""
Utility module for outbound LINE notifications.

Put *all* LINE‑messaging logic here so that other modules
(api.main, scheduler.job_runner, etc.) can simply:

    from backend.utils.notification import send_line_message
"""

import os
from fastapi import HTTPException
from linebot import LineBotApi
from linebot.models import TextSendMessage

# ---------------------------------------------------------------------------
# Environment variables (Cloud Run / Docker ― set via --set-env-vars)
# ---------------------------------------------------------------------------
LINE_CHANNEL_TOKEN: str = os.getenv("LINE_CHANNEL_TOKEN", "")
LINE_USER_ID: str = os.getenv("LINE_USER_ID", "")

# Initialise client only if token is present to avoid crashing on import.
_line_api: LineBotApi | None = (
    LineBotApi(LINE_CHANNEL_TOKEN) if LINE_CHANNEL_TOKEN else None
)


def send_line_message(text: str) -> None:
    """
    Send a LINE push message to the configured user.

    Raises
    ------
    HTTPException
        * 500 if the token / user‑ID is not configured
        * 500 if the underlying LINE SDK raises an error
    """
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID or _line_api is None:
        raise HTTPException(
            status_code=500,
            detail="LINE API token or user ID not configured",
        )

    try:
        _line_api.push_message(LINE_USER_ID, TextSendMessage(text=text))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
