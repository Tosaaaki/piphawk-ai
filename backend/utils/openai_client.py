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

# env_loader automatically loads default .env files at import time

# Get OpenAI API key from environment
OPENAI_API_KEY = env_loader.get_env("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment variables.")

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

# Default model can be overridden via settings.env → AI_MODEL
AI_MODEL = env_loader.get_env("AI_MODEL", "gpt-4.1-nano")

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
            to ``client.chat.completions.create``. Defaults to requesting a
            JSON object when not provided.
    Returns:
        dict: Parsed JSON object returned by the assistant.
    Raises:
        Exception: If the API request fails.
    """
    # Use env‑defined default when caller does not specify
    if model is None:
        model = AI_MODEL
    try:
        if response_format is None:
            response_format = {"type": "json_object"}

        response = client.chat.completions.create(
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
        return json.loads(response_content)
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


__all__ = ["ask_openai", "ask_openai_async", "AI_MODEL"]
