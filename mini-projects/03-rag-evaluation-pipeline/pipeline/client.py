"""API client factory for QA generation (Anthropic by default, OpenAI/OpenRouter optional).

Embeddings run locally (see ``embedder.py``), so the only API key the pipeline
needs is a chat key for synthetic QA generation. ``QA_PROVIDER`` selects the
backend; all backends are returned as an Instructor client exposing the unified
``chat.completions.create(..., response_model=...)`` interface.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import instructor
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ENV_SEARCH_PATHS = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]

for _p in _ENV_SEARCH_PATHS:
    if _p.exists():
        load_dotenv(_p)
        break

DEFAULT_QA_MODEL = "claude-haiku-4-5-20251001"


def get_openai_client():
    from openai import OpenAI

    kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"]}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def get_openrouter_client():
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set; falling back to OpenAI client")
        return get_openai_client()
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def get_anthropic_instructor_client() -> instructor.Instructor:
    import anthropic

    return instructor.from_anthropic(anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]))


def get_qa_client() -> instructor.Instructor:
    """Return an Instructor client for the configured ``QA_PROVIDER``."""
    provider = os.environ.get("QA_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return get_anthropic_instructor_client()
    if provider == "openrouter":
        return instructor.from_openai(get_openrouter_client())
    if provider == "openai":
        return instructor.from_openai(get_openai_client())
    raise ValueError(f"Unknown QA_PROVIDER: {provider}")


def get_qa_model_name() -> str:
    return os.environ.get("QA_MODEL_NAME", DEFAULT_QA_MODEL)


def get_qa_max_tokens() -> int:
    return int(os.environ.get("QA_MAX_TOKENS", "1024"))


# Backwards-compatible alias.
def get_instructor_client() -> instructor.Instructor:
    return get_qa_client()
