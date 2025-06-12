try:
    from openai import OpenAI, APIError
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "openai package is required. Install via 'pip install openai'."
    ) from exc
from backend.utils import env_loader
import json
import logging
import asyncio
import time
from typing import Dict, Tuple, Optional
from collections import OrderedDict

# env_loader はインポート時に既定の .env を読み込む

# OpenAI クライアントは初回呼び出し時に生成する
client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Return an initialized OpenAI client."""
    global client
    if client is None:
        api_key = env_loader.get_env("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment variables.")
        client = OpenAI(api_key=api_key)
    return client

logger = logging.getLogger(__name__)

# Default model can be overridden via settings.env → AI_MODEL
AI_MODEL = env_loader.get_env("AI_MODEL", "gpt-4.1-nano")

# ──────────────────────────────────
#   Lightweight in-memory cache
# ──────────────────────────────────
_cache: "OrderedDict[Tuple[str, str, str], Tuple[float, dict]]" = OrderedDict()
_CACHE_TTL_SEC = int(env_loader.get_env("OPENAI_CACHE_TTL_SEC", "30"))
_CACHE_MAX = int(env_loader.get_env("OPENAI_CACHE_MAX", "100"))

# --- AI 呼び出し制御 ----------------------------
_CALL_LIMIT_PER_LOOP = int(env_loader.get_env("MAX_AI_CALLS_PER_LOOP", "4"))
_calls_this_loop = 0


def reset_ai_call_counter() -> None:
    """Reset the AI call counter (JobRunner が各ループ開始時に呼び出す)."""
    global _calls_this_loop
    _calls_this_loop = 0


def _register_ai_call() -> bool:
    """Return True if a new AI call is allowed in this loop."""
    global _calls_this_loop
    if _CALL_LIMIT_PER_LOOP > 0 and _calls_this_loop >= _CALL_LIMIT_PER_LOOP:
        logger.info("AI call skipped due to per-loop limit")
        return False
    _calls_this_loop += 1
    return True


def set_call_limit(limit: int) -> None:
    """Update the per-loop AI call limit."""
    global _CALL_LIMIT_PER_LOOP
    _CALL_LIMIT_PER_LOOP = int(limit)

def ask_openai(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    *,
    max_tokens: int = 512,
    temperature: float = 0.7,
    response_format: dict | None = None,
) -> dict:
    """
    Send a prompt to OpenAI's API and return the response text.
    Args:
        prompt (str): The user prompt/question.
        system_prompt (str): The system message (instructions for the assistant).
        model (str): The OpenAI model to use.
        response_format (dict | None): Optional response_format passed directly
            to the OpenAI client's ``chat.completions.create`` method.
            Defaults to requesting a JSON object when not provided.
    Returns:
        dict: Parsed JSON object returned by the assistant.
    Raises:
        Exception: If the API request fails.
    """
    # ループ開始時に呼び出し許可を確認
    if not _register_ai_call():
        return {}

    # Use env‑defined default when caller does not specify
    if model is None:
        model = AI_MODEL

    key = (model, system_prompt, prompt)
    now = time.time()
    cached = _cache.get(key)
    if cached:
        if now - cached[0] < _CACHE_TTL_SEC:
            logger.debug("OpenAI cache hit for %s", model)
            _cache.move_to_end(key)
            return cached[1]
        else:
            _cache.pop(key, None)
    try:
        if response_format is None:
            response_format = {"type": "json_object"}

        openai_client = _get_client()
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )
        response_content = response.choices[0].message.content.strip()
        parsed = json.loads(response_content)
        _cache[key] = (now, parsed)
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
        return parsed
    except json.JSONDecodeError as exc:
        logger.error("Malformed JSON from OpenAI: %s", response_content)
        raise RuntimeError("Invalid JSON response") from exc
    except APIError as e:
        raise RuntimeError(f"OpenAI API request failed: {e}") from e


async def ask_openai_async(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    *,
    max_tokens: int = 512,
    temperature: float = 0.7,
    response_format: dict | None = None,
) -> dict:
    """Non-blocking wrapper around ``ask_openai``."""

    return await asyncio.to_thread(
        ask_openai,
        prompt,
        system_prompt=system_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format=response_format,
    )


__all__ = [
    "ask_openai",
    "ask_openai_async",
    "AI_MODEL",
    "reset_ai_call_counter",
    "set_call_limit",
]
