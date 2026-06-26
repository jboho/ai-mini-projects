"""LLM client factory.

The PLAN specifies Groq via its OpenAI-compatible endpoint; we use the OpenAI API
directly (the available key is OpenAI) through the same SDK. Everything downstream
takes an injectable ``llm`` callable, so swapping providers only touches this module.
"""

from __future__ import annotations

from collections.abc import Callable

from .config import get_settings


def get_client():
    """OpenAI-compatible client (works for OpenAI or any OpenAI-compatible base URL)."""
    from openai import OpenAI

    settings = get_settings()
    kwargs: dict = {"api_key": settings.openai_api_key or None}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def get_model_name() -> str:
    return get_settings().model_name


def llm_complete(prompt: str, model: str | None = None, temperature: float = 0.0) -> str:
    """Plain-text chat completion. Reused for classification fallback, agents, judging."""
    client = get_client()
    resp = client.chat.completions.create(
        model=model or get_model_name(),
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def get_llm() -> Callable[[str], str] | None:
    """The injectable LLM callable, or None when no API key is configured (offline)."""
    return llm_complete if get_settings().openai_api_key else None
