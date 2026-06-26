"""Source loaders + a helper to load and combine all sources."""

from __future__ import annotations

from ..models import Feedback
from .amazon import AmazonLoader
from .appstore import AppStoreLoader
from .base import BaseLoader
from .yelp import YelpLoader

LOADERS = {"amazon": AmazonLoader, "yelp": YelpLoader, "app_store": AppStoreLoader}

__all__ = ["AmazonLoader", "AppStoreLoader", "BaseLoader", "YelpLoader", "load_all_sources"]


def load_all_sources(
    sample_size: int, min_length: int = 30, sources: list[str] | None = None
) -> list[Feedback]:
    sources = sources or list(LOADERS)
    per_source = max(1, sample_size // len(sources))
    feedback: list[Feedback] = []
    for name in sources:
        feedback.extend(LOADERS[name]().load(per_source, min_length))
    return feedback
