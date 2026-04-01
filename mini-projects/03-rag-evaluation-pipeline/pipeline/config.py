"""Pipeline configuration and grid search parameter definitions."""

from __future__ import annotations

import enum
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ParserType(str, enum.Enum):
    PDFPLUMBER = "pdfplumber"
    PYPDF2 = "pypdf2"
    PYMUPDF = "pymupdf"


class ChunkMethod(str, enum.Enum):
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    SEMANTIC = "semantic"


class RetrievalMethod(str, enum.Enum):
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"


class PipelineSettings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_api_key: str = ""
    qa_model_name: str = "deepseek/deepseek-r1-0528:free"
    cohere_api_key: str = ""
    num_questions_per_config: int = 20

    model_config = {"env_file": ".env", "extra": "ignore"}


class ChunkingConfig(BaseModel):
    parser: ParserType = ParserType.PDFPLUMBER
    method: ChunkMethod
    chunk_size: int = 256
    overlap: int = 50
    sentences_per_chunk: int = 5
    overlap_sentences: int = 1
    max_tokens: int = 300

    @property
    def label(self) -> str:
        if self.method == ChunkMethod.FIXED_SIZE:
            return f"{self.parser.value}_{self.method.value}_cs{self.chunk_size}_ov{self.overlap}"
        if self.method == ChunkMethod.SENTENCE:
            return f"{self.parser.value}_{self.method.value}_spc{self.sentences_per_chunk}_ov{self.overlap_sentences}"
        return f"{self.parser.value}_{self.method.value}_mt{self.max_tokens}"

    @property
    def cache_key(self) -> str:
        blob = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


EMBEDDING_MODELS: list[str] = [
    "text-embedding-3-small",
    "text-embedding-3-large",
]

RETRIEVAL_METHODS: list[RetrievalMethod] = [
    RetrievalMethod.BM25,
    RetrievalMethod.VECTOR,
    RetrievalMethod.HYBRID,
]

K_VALUES: list[int] = [1, 3, 5, 10]

DEFAULT_CHUNKING_CONFIGS: list[ChunkingConfig] = [
    ChunkingConfig(method=ChunkMethod.FIXED_SIZE, chunk_size=256, overlap=50),
    ChunkingConfig(method=ChunkMethod.FIXED_SIZE, chunk_size=512, overlap=100),
    ChunkingConfig(method=ChunkMethod.SENTENCE, sentences_per_chunk=5, overlap_sentences=1),
    ChunkingConfig(method=ChunkMethod.SEMANTIC, max_tokens=300),
]


class GridSearchConfig(BaseModel):
    chunking_configs: list[ChunkingConfig] = Field(
        default_factory=lambda: list(DEFAULT_CHUNKING_CONFIGS),
    )
    embedding_models: list[str] = Field(
        default_factory=lambda: list(EMBEDDING_MODELS),
    )
    retrieval_methods: list[RetrievalMethod] = Field(
        default_factory=lambda: list(RETRIEVAL_METHODS),
    )
    k_values: list[int] = Field(default_factory=lambda: list(K_VALUES))
    num_questions: int = 20
    hybrid_alpha: float = 0.5

    @property
    def total_experiments(self) -> int:
        return (
            len(self.chunking_configs)
            * len(self.embedding_models)
            * len(self.retrieval_methods)
        )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "cache"
RESULTS_DIR = PROJECT_ROOT / "results"
