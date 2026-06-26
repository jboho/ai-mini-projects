"""Typed settings + filesystem paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

for _p in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent.parent / ".env"):
    if _p.exists():
        load_dotenv(_p)
        break


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = ""
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    database_url: str = "sqlite:///data/tawos.db"
    chromadb_path: str = "data/chromadb"
    tawos_projects: str = "APACHE"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def project_keys(self) -> list[str]:
        return [p.strip() for p in self.tawos_projects.split(",") if p.strip()]


def get_settings() -> Settings:
    return Settings()


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gpt-4o-mini")
