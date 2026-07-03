"""OpenAI client factory and model-name helpers (CrewAI agents use these)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_SEARCH_PATHS = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]

for _p in _ENV_SEARCH_PATHS:
    if _p.exists():
        load_dotenv(_p)
        break


def get_openai_client():
    from openai import OpenAI

    kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"]}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gpt-4o-mini")


def get_embedding_model_name() -> str:
    return os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
