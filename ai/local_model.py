"""OpenAI 互換のローカルモデル呼び出しラッパー"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from backend.utils import env_loader, openai_client

logger = logging.getLogger(__name__)

USE_LOCAL_MODEL = env_loader.get_env("USE_LOCAL_MODEL", "false").lower() == "true"
LOCAL_MODEL_NAME = env_loader.get_env("LOCAL_MODEL_NAME", "distilgpt2")

_pipeline = None


def _load_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline

            _pipeline = pipeline("text-generation", model=LOCAL_MODEL_NAME)
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.error("Failed to load local model: %s", exc)
            raise
    return _pipeline


def ask_model(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    **kwargs: Any,
) -> dict:
    """OpenAI API と互換の返値を持つモデル呼び出し"""
    if USE_LOCAL_MODEL:
        pipe = _load_pipeline()
        try:
            outputs = pipe(prompt, max_new_tokens=256)
            text = outputs[0]["generated_text"]
            try:
                return json.loads(text)
            except Exception:
                return {"text": text}
        except Exception as exc:
            logger.error("Local model inference failed: %s", exc)
            raise
    else:
        return openai_client.ask_openai(
            prompt,
            system_prompt=system_prompt,
            model=model,
            **kwargs,
        )


async def ask_model_async(
    prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    model: str | None = None,
    *,
    fallback_to_local: bool = True,
    **kwargs: Any,
) -> dict:
    """Async wrapper that falls back to the local model when OpenAI fails."""

    if USE_LOCAL_MODEL:
        return await asyncio.to_thread(
            ask_model,
            prompt,
            system_prompt=system_prompt,
            model=model,
            **kwargs,
        )
    try:
        return await openai_client.ask_openai_async(
            prompt,
            system_prompt=system_prompt,
            model=model,
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - network failure
        logger.warning("ask_model_async fallback to local model: %s", exc)
        if fallback_to_local:
            return await asyncio.to_thread(
                ask_model,
                prompt,
                system_prompt=system_prompt,
                model=model,
                **kwargs,
            )
        raise


__all__ = ["ask_model", "ask_model_async", "USE_LOCAL_MODEL"]
