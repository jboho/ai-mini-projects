"""Sequential orchestration: load -> sentiment -> theme -> map -> gap -> evaluate."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from .agents.gap import GapAgent
from .agents.mapping import MappingAgent
from .agents.sentiment import SentimentAgent
from .agents.theme import ThemeAgent
from .config import DATA_DIR, ROADMAP_PATH, PipelineConfig
from .evaluation import pain_calibration, sentiment_accuracy
from .loaders import load_all_sources
from .models import (
    AlignmentResult,
    Feedback,
    GapAnalysis,
    RoadmapItem,
    SentimentResult,
    Theme,
)

logger = logging.getLogger(__name__)


class PipelineOutput(BaseModel):
    feedback: list[Feedback] = Field(default_factory=list)
    sentiments: list[SentimentResult] = Field(default_factory=list)
    themes: list[Theme] = Field(default_factory=list)
    alignments: list[AlignmentResult] = Field(default_factory=list)
    gaps: list[GapAnalysis] = Field(default_factory=list)
    evaluation: dict = Field(default_factory=dict)


def load_roadmap(path: str | Path | None = None) -> list[RoadmapItem]:
    path = Path(path) if path else ROADMAP_PATH
    return [RoadmapItem(**item) for item in json.loads(path.read_text())]


def run_pipeline(
    config: PipelineConfig,
    sources: list[str] | None = None,
    sample_size: int | None = None,
    roadmap_path: str | Path | None = None,
    stop_after: str = "full",
    on_event=None,
) -> PipelineOutput:
    def emit(msg: str) -> None:
        logger.info(msg)
        if on_event:
            on_event(msg)

    sample_size = sample_size or config.sample_size
    emit(f"Loading feedback (sample {sample_size})...")
    feedback = load_all_sources(sample_size, config.min_review_length, sources)
    out = PipelineOutput(feedback=feedback)
    emit(f"Loaded {len(feedback)} feedback items.")
    if stop_after == "ingest-only":
        return out

    emit("Scoring sentiment + pain...")
    out.sentiments = SentimentAgent(config.model_name).analyze_batch(feedback)
    out.evaluation = {
        "sentiment_accuracy": sentiment_accuracy(feedback, out.sentiments),
        "pain_calibration": pain_calibration(feedback, out.sentiments),
    }
    if stop_after == "sentiment-only":
        return out

    emit("Extracting themes...")
    out.themes = ThemeAgent(config.model_name).extract(feedback, out.sentiments, config.max_themes)
    emit("Mapping themes to roadmap...")
    roadmap = load_roadmap(roadmap_path)
    out.alignments = MappingAgent(config.similarity_threshold).map(out.themes, roadmap)
    emit("Analyzing gaps + recommendations...")
    out.gaps = GapAgent(config.priority_weights, config.model_name).analyze(
        out.themes, out.alignments, out.sentiments
    )
    return out


def save_output(output: PipelineOutput, directory: str | Path | None = None) -> Path:
    directory = Path(directory) if directory else DATA_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "pipeline_output.json"
    path.write_text(output.model_dump_json(indent=2))
    return path


def load_output(directory: str | Path | None = None) -> PipelineOutput:
    directory = Path(directory) if directory else DATA_DIR
    return PipelineOutput.model_validate_json((directory / "pipeline_output.json").read_text())
