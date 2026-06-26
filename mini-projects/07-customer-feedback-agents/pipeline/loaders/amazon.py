"""Amazon reviews loader (title + text, float rating -> int)."""

from __future__ import annotations

from ..models import Feedback
from .base import BaseLoader, make_id


class AmazonLoader(BaseLoader):
    source = "amazon"

    def __init__(
        self,
        dataset: str = "McAuley-Lab/Amazon-Reviews-2023",
        subset: str = "raw_review_All_Beauty",
    ) -> None:
        self.dataset = dataset
        self.subset = subset

    def load_raw(self, sample_size: int) -> list[dict]:
        from datasets import load_dataset

        stream = load_dataset(
            self.dataset, self.subset, split="full", streaming=True, trust_remote_code=True
        )
        return list(stream.take(sample_size * 2))

    def normalize(self, raw: dict) -> Feedback | None:
        title = (raw.get("title") or "").strip()
        text = (raw.get("text") or "").strip()
        full = f"{title}\n{text}".strip() if title else text
        if not full:
            return None
        rating = raw.get("rating")
        return Feedback(
            id=make_id(self.source, full),
            source="amazon",
            text=full,
            rating=int(rating) if rating is not None else None,
            metadata={
                "asin": raw.get("asin"),
                "helpful_vote": raw.get("helpful_vote"),
                "verified_purchase": raw.get("verified_purchase"),
            },
        )
