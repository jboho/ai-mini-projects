"""Pipeline configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Search for .env in project root first, then workspace root
_ENV_CANDIDATES = [
    _PROJECT_ROOT / ".env",
    _PROJECT_ROOT.parent.parent / ".env",
]
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.exists()), _PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"

    batch_size: int = 5
    resumes_per_job: int = 3
    max_correction_retries: int = 3
    enable_judge: bool = False

    data_dir: Path = _PROJECT_ROOT / "data"
    visuals_dir: Path = _PROJECT_ROOT / "visuals"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.visuals_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    return Settings()
