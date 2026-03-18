"""Centralized API client factory for OpenAI, OpenRouter, and Instructor."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import instructor
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

_ENV_SEARCH_PATHS = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]

for _p in _ENV_SEARCH_PATHS:
    if _p.exists():
        load_dotenv(_p)
        break


def get_openai_client() -> OpenAI:
    kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"]}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def get_openrouter_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning(
            "OPENROUTER_API_KEY not set; falling back to OpenAI client"
        )
        return get_openai_client()
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def get_instructor_client() -> instructor.Instructor:
    return instructor.from_openai(get_openrouter_client())


def get_qa_model_name() -> str:
    return os.environ.get("QA_MODEL_NAME", "deepseek/deepseek-r1-0528:free")
