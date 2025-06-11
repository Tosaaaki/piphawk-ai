import os
import time
import logging
import requests

# Global HTTP session to leverage connection pooling
_SESSION = requests.Session()

# Retry/backoff settings from environment
HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "3"))
HTTP_BACKOFF_CAP_SEC = int(os.getenv("HTTP_BACKOFF_CAP_SEC", "8"))
HTTP_TIMEOUT_SEC = int(os.getenv("HTTP_TIMEOUT_SEC", "10"))

logger = logging.getLogger(__name__)

def request_with_retries(method: str, url: str, **kwargs) -> object:
    """HTTPリクエストをリトライ付きで実行するユーティリティ"""
    wait = 1
    for attempt in range(HTTP_MAX_RETRIES):
        try:
            headers = kwargs.pop("headers", None)
            timeout = kwargs.pop("timeout", HTTP_TIMEOUT_SEC)
            if hasattr(_SESSION, "request"):
                resp = _SESSION.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )
            else:
                req_func = getattr(requests, method.lower())
                try:
                    resp = req_func(
                        url,
                        headers=headers,
                        timeout=timeout,
                        **kwargs,
                    )
                except TypeError:
                    resp = req_func(
                        url,
                        headers=headers,
                        **kwargs,
                    )
        except Exception as exc:
            if attempt == HTTP_MAX_RETRIES - 1:
                raise
            logger.warning(f"Request error: {exc} – retrying in {wait}s")
        else:
            if resp.status_code not in (429,) and not 500 <= resp.status_code < 600:
                return resp
            if attempt == HTTP_MAX_RETRIES - 1:
                return resp
            logger.warning(
                "HTTP %s returned %s – retrying in %ss",
                method.upper(),
                resp.status_code,
                wait,
            )
        time.sleep(min(wait, HTTP_BACKOFF_CAP_SEC))
        wait = min(wait * 2, HTTP_BACKOFF_CAP_SEC)
    return resp
