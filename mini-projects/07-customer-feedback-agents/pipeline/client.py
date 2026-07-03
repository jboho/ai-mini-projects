"""OpenAI + Instructor client factory."""

from __future__ import annotations

import os

import instructor


def get_openai_client():
    from openai import OpenAI

    kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"]}
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def get_instructor_client() -> instructor.Instructor:
    return instructor.from_openai(get_openai_client())


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gpt-4o-mini")
