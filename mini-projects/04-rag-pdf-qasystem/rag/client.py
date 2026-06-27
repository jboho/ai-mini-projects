"""Chat client factory for answer generation and the LLM judge.

Embeddings and cross-encoder reranking are local; the only API key needed is a
chat key. ``QA_PROVIDER`` selects the backend. All backends are returned as an
Instructor client exposing ``chat.completions.create(..., response_model=...)``.
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


def _openai_client():
    from openai import OpenAI

    kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"]}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _openrouter_client():
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set; falling back to OpenAI client")
        return _openai_client()
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def get_chat_client() -> instructor.Instructor:
    """Return an Instructor client for the configured ``QA_PROVIDER``."""
    provider = os.environ.get("QA_PROVIDER", "openrouter").lower()
    if provider == "anthropic":
        import anthropic

        return instructor.from_anthropic(
            anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        )
    if provider == "openai":
        return instructor.from_openai(_openai_client())
    if provider == "openrouter":
        return instructor.from_openai(_openrouter_client())
    raise ValueError(f"Unknown QA_PROVIDER: {provider}")


def get_qa_model_name() -> str:
    return os.environ.get("QA_MODEL_NAME", "google/gemma-4-31b-it:free")


def get_judge_model_name() -> str:
    return os.environ.get("JUDGE_MODEL_NAME", get_qa_model_name())


def get_qa_max_tokens() -> int:
    return int(os.environ.get("QA_MAX_TOKENS", "1024"))
