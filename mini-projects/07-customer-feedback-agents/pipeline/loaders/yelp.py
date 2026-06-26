"""Yelp reviews loader (label 0-4 -> 1-5 stars)."""

from __future__ import annotations

from ..models import Feedback
from .base import BaseLoader, make_id


class YelpLoader(BaseLoader):
    source = "yelp"

    def __init__(self, dataset: str = "yelp_review_full") -> None:
        self.dataset = dataset

    def load_raw(self, sample_size: int) -> list[dict]:
        from datasets import load_dataset

        stream = load_dataset(self.dataset, split="train", streaming=True)
        return list(stream.take(sample_size))

    def normalize(self, raw: dict) -> Feedback | None:
        text = (raw.get("text") or "").strip()
        if not text:
            return None
        label = raw.get("label")
        return Feedback(
            id=make_id(self.source, text),
            source="yelp",
            text=text,
            rating=int(label) + 1 if label is not None else None,
        )
