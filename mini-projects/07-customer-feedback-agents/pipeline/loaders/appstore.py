"""App Store reviews loader (review field, star rating, date parsing)."""

from __future__ import annotations

from ..models import Feedback
from .base import BaseLoader, make_id


class AppStoreLoader(BaseLoader):
    source = "app_store"

    def __init__(self, dataset: str = "app_reviews") -> None:
        self.dataset = dataset

    def load_raw(self, sample_size: int) -> list[dict]:
        from datasets import load_dataset

        stream = load_dataset(self.dataset, split="train", streaming=True, trust_remote_code=True)
        return list(stream.take(sample_size * 2))

    def normalize(self, raw: dict) -> Feedback | None:
        text = (raw.get("review") or raw.get("text") or "").strip()
        if not text:
            return None
        star = raw.get("star") or raw.get("rating")
        date = raw.get("date")
        return Feedback(
            id=make_id(self.source, text),
            source="app_store",
            text=text,
            rating=int(star) if star is not None else None,
            date=str(date) if date else None,
            metadata={"package_name": raw.get("package_name")},
        )
