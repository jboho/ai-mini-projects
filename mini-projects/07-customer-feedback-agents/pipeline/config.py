"""Settings (env) + YAML pipeline config + filesystem paths."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VISUALS_DIR = PROJECT_ROOT / "visuals"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ROADMAP_PATH = PROJECT_ROOT / "roadmap.json"

for _p in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent.parent / ".env"):
    if _p.exists():
        load_dotenv(_p)
        break


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    model_config = {"env_file": ".env", "extra": "ignore"}


class PriorityWeights(BaseModel):
    pain: float = 0.35
    frequency: float = 0.25
    coverage: float = 0.25
    sentiment: float = 0.15


class PipelineConfig(BaseModel):
    sample_size: int = 3000
    min_review_length: int = 30
    similarity_threshold: float = 0.75
    gap_priority_threshold: float = 0.6
    max_themes: int = 10
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    priority_weights: PriorityWeights = Field(default_factory=PriorityWeights)
    product_areas: list[str] = Field(default_factory=list)


def load_config(path: str | Path | None = None) -> PipelineConfig:
    path = Path(path) if path else CONFIG_PATH
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    return PipelineConfig(**data)


def get_settings() -> Settings:
    return Settings()


def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gpt-4o-mini")
