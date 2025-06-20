import base64
import json


def sanitize_comment(comment: str, max_bytes: int = 240) -> str:
    """Remove newlines and enforce max byte length for OANDA."""
    sanitized = comment.replace("\n", " ").replace("\r", " ")
    if len(sanitized.encode("utf-8")) > max_bytes:
        sanitized = sanitized.encode("utf-8")[:max_bytes].decode("utf-8", "ignore")
    return sanitized


def encode_comment(data: dict) -> str:
    """Encode comment data as URL-safe base64 JSON."""
    raw = json.dumps(data, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(raw.encode()).decode()
    return sanitize_comment(encoded)


def decode_comment(comment: str) -> dict | None:
    """Decode comment from base64 or plain JSON."""
    if not comment:
        return None
    try:
        raw = base64.urlsafe_b64decode(comment.encode()).decode()
        return json.loads(raw)
    except Exception:
        try:
            return json.loads(comment)
        except Exception:
            return None
