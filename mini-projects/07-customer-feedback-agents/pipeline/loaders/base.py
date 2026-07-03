"""BaseLoader ABC: load_raw (download) + normalize (pure) -> filtered Feedback."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Feedback


def make_id(source: str, text: str) -> str:
    return f"{source}_{abs(hash(text)) % 10**10}"


class BaseLoader(ABC):
    source: str = "base"

    @abstractmethod
    def load_raw(self, sample_size: int) -> list[dict]:
        """Fetch up to ``sample_size`` raw records from the source."""

    @abstractmethod
    def normalize(self, raw: dict) -> Feedback | None:
        """Convert one raw record into a Feedback (or None if unusable)."""

    def load(self, sample_size: int, min_length: int = 30) -> list[Feedback]:
        results: list[Feedback] = []
        for raw in self.load_raw(sample_size):
            fb = self.normalize(raw)
            if fb and len(fb.text) >= min_length:
                results.append(fb)
        return results
