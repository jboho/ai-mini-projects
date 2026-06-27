"""OpenAI + Instructor client factory."""

from __future__ import annotations

import instructor
from openai import OpenAI

from .config import Settings, get_settings


def get_instructor_client(settings: Settings | None = None) -> instructor.Instructor:
    s = settings or get_settings()
    raw = OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)
    return instructor.from_openai(raw)


def get_openai_client(settings: Settings | None = None) -> OpenAI:
    s = settings or get_settings()
    return OpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)
