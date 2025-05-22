import json
import logging
from typing import Any, Tuple, Dict

logger = logging.getLogger(__name__)

def parse_json_answer(raw: str | dict) -> Tuple[Dict[str, Any] | None, Exception | None]:
    """Safely parse an OpenAI answer that may be a dict or JSON string.

    Parameters
    ----------
    raw : str | dict
        Raw response from the language model.

    Returns
    -------
    tuple
        (parsed_dict or None, exception or None)
    """
    if isinstance(raw, dict):
        return raw, None
    try:
        return json.loads(str(raw).strip()), None
    except Exception as exc:  # json.JSONDecodeError and others
        logger.error("Failed to parse JSON answer: %s", raw)
        return None, exc
