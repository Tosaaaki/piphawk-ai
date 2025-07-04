"""Thin wrapper around the OpenAI client with optional lazy import."""

try:  # Lazy import when available
    from openai import APIError as _APIError
    from openai import OpenAI as _OpenAI
    APIError = _APIError
    OpenAI = _OpenAI
except Exception:  # pragma: no cover - allow tests without openai
    APIError = Exception
    OpenAI = None
import asyncio
import json
import logging
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

try:
    import tiktoken  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    tiktoken = None

from backend.utils import env_loader
from backend.utils.rate_limiter import TokenBucket

# env_loader はインポート時に既定の .env を読み込む

# OpenAI クライアントは初回呼び出し時に生成する
client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Return an initialized OpenAI client."""
    global client, OpenAI
    if client is None:
        if OpenAI is None:
            try:  # Import lazily to avoid hard dependency during tests
                from openai import OpenAI as _OpenAI
                OpenAI = _OpenAI
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("openai package is required") from exc
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
_bucket = TokenBucket(rate=120)


def set_call_limit(_limit: int) -> None:
    """Set the maximum number of OpenAI calls allowed per loop."""
    global _CALL_LIMIT_PER_LOOP, _calls_this_loop
    _CALL_LIMIT_PER_LOOP = _limit
    _calls_this_loop = 0


def reset_call_counter() -> None:
    """Reset the per-loop OpenAI call counter."""
    global _calls_this_loop
    _calls_this_loop = 0

def ask_openai(
    prompt: str | None = None,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    *,
    max_tokens: int = 512,
    temperature: float = 0.7,
    response_format: dict | None = None,
    n: int = 1,
    messages: List[Dict[str, str]] | None = None,
) -> dict | list[dict]:
    """
    Send a prompt or prepared message list to OpenAI's API and return the response.
    Args:
        prompt (str | None): The user prompt/question when ``messages`` is not used.
        system_prompt (str): The system message (ignored when ``messages`` is given).
        model (str): The OpenAI model to use.
        response_format (dict | None): Optional response_format passed directly
            to the OpenAI client's ``chat.completions.create`` method.
            Defaults to requesting a JSON object when not provided.
        messages (list[dict] | None): Pre-composed message list overriding
            ``prompt`` and ``system_prompt``.
    Returns:
        dict or list[dict]: Parsed JSON object(s) returned by the assistant.
    Raises:
        Exception: If the API request fails.
    """

    global _calls_this_loop

    # Use env‑defined default when caller does not specify
    if model is None:
        model = AI_MODEL

    if _calls_this_loop >= _CALL_LIMIT_PER_LOOP:
        raise RuntimeError("OpenAI call limit exceeded")
    _calls_this_loop += 1
    _bucket.acquire()

    if messages is not None:
        cache_prompt = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        key = (model, "messages", cache_prompt)
    else:
        cache_prompt = prompt or ""
        key = (model, system_prompt, cache_prompt)
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
        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt or ""},
            ]
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            n=n,
        )
        results = []
        for choice in response.choices:
            response_content = choice.message.content.strip()
            results.append(json.loads(response_content))
        parsed = results[0] if n == 1 else results
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
    n: int = 1,
) -> dict | list[dict]:
    """Non-blocking wrapper around ``ask_openai``."""

    return await asyncio.to_thread(
        ask_openai,
        prompt,
        system_prompt=system_prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format=response_format,
        n=n,
    )


def num_tokens(messages: List[Dict[str, str]], model: str | None = None) -> int:
    """Return token count for message list."""

    if model is None:
        model = AI_MODEL

    if tiktoken is None:
        return sum(len(m.get("content", "")) // 4 for m in messages)

    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:  # pragma: no cover - unknown model
        enc = tiktoken.get_encoding("cl100k_base")

    tokens_per_message = 4 if model.startswith("gpt-3.5") else 3
    tokens_per_name = -1 if model.startswith("gpt-3.5") else 1

    count = 0
    for msg in messages:
        count += tokens_per_message
        for k, v in msg.items():
            count += len(enc.encode(v))
            if k == "name":
                count += tokens_per_name
    return count + 3


def trim_tokens(
    messages: List[Dict[str, str]],
    limit: int,
    *,
    model: str | None = None,
) -> List[Dict[str, str]]:
    """Trim messages so total tokens do not exceed *limit*."""

    trimmed = list(messages)
    while len(trimmed) > 1 and num_tokens(trimmed, model=model) > limit:
        for i, msg in enumerate(trimmed):
            if msg.get("role") != "system":
                trimmed.pop(i)
                break
        else:
            break
    return trimmed


__all__ = [
    "ask_openai",
    "ask_openai_async",
    "num_tokens",
    "trim_tokens",
    "AI_MODEL",
    "set_call_limit",
    "reset_call_counter",
]
