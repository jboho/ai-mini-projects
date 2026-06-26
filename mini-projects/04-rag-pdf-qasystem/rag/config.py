"""Pipeline settings, filesystem paths, and YAML-driven run/experiment config."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PAPERS_DIR = DATA_DIR / "papers"
CORPUS_DIR = DATA_DIR / "corpus"
INDICES_DIR = DATA_DIR / "indices"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
CONFIG_DIR = PROJECT_ROOT / "config"


class PipelineSettings(BaseSettings):
    # Generation/judge run through a chat provider; embeddings + cross-encoder
    # reranking are local, so only a chat key is required.
    qa_provider: str = "openrouter"
    qa_model_name: str = "google/gemma-4-31b-it:free"
    judge_model_name: str = "google/gemma-4-31b-it:free"
    qa_max_tokens: int = 1024

    openrouter_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    cohere_api_key: str = ""

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = {"env_file": ".env", "extra": "ignore"}


class ComponentConfig(BaseModel):
    name: str
    params: dict = Field(default_factory=dict)


class RunConfig(BaseModel):
    """A single resolved pipeline configuration (one grid cell)."""

    chunker: ComponentConfig
    embedder: str = "sentence-transformers/all-MiniLM-L6-v2"
    retriever: ComponentConfig = Field(default_factory=lambda: ComponentConfig(name="hybrid"))
    reranker: str | None = None
    top_k: int = 10
    k_values: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])

    @property
    def label(self) -> str:
        rr = self.reranker or "none"
        return (
            f"{self.chunker.name}__{self.embedder.split('/')[-1]}__{self.retriever.name}__rr-{rr}"
        )

    @property
    def cache_key(self) -> str:
        blob = json.dumps(
            {"chunker": self.chunker.model_dump(), "embedder": self.embedder},
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


def load_yaml(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def load_default_config(path: str | Path | None = None) -> RunConfig:
    path = Path(path) if path else CONFIG_DIR / "default.yaml"
    return RunConfig(**load_yaml(path))


def load_experiment_grid(path: str | Path | None = None) -> list[RunConfig]:
    """Expand an experiment YAML (lists of components) into RunConfig cells."""
    path = Path(path) if path else CONFIG_DIR / "experiments" / "baseline.yaml"
    spec = load_yaml(path)

    chunkers = [ComponentConfig(**c) for c in spec["chunkers"]]
    embedders = spec["embedders"]
    retrievers = [ComponentConfig(**r) for r in spec["retrievers"]]
    rerankers = spec.get("rerankers", [None])
    top_k = spec.get("top_k", 10)
    k_values = spec.get("k_values", [1, 3, 5, 10])

    configs: list[RunConfig] = []
    for chunker, embedder, retriever, reranker in itertools.product(
        chunkers, embedders, retrievers, rerankers
    ):
        configs.append(
            RunConfig(
                chunker=chunker,
                embedder=embedder,
                retriever=retriever,
                reranker=reranker,
                top_k=top_k,
                k_values=k_values,
            )
        )
    return configs
