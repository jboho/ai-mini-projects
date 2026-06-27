"""Centralized OpenAI + Instructor client factory."""

from __future__ import annotations

import os
from pathlib import Path

import instructor
from dotenv import load_dotenv
from openai import OpenAI

_ENV_SEARCH_PATHS = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]

for _p in _ENV_SEARCH_PATHS:
    if _p.exists():
        load_dotenv(_p)
        break


def _get_raw_client() -> OpenAI:
    kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"]}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def get_instructor_client() -> instructor.Instructor:
    return instructor.from_openai(_get_raw_client())


def get_openai_client() -> OpenAI:
    return _get_raw_client()


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gpt-4o-mini")
