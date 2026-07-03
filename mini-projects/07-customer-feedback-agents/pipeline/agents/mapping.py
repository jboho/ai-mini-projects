"""MappingAgent: align themes to roadmap items by embedding cosine similarity."""

from __future__ import annotations

import numpy as np

from ..embeddings import cosine_matrix, embed_texts
from ..models import AlignmentResult, RoadmapItem, Theme


def align_from_matrix(
    themes: list[Theme],
    roadmap: list[RoadmapItem],
    sim: np.ndarray,
    threshold: float,
) -> list[AlignmentResult]:
    """Pure: for each theme pick its best roadmap match above the threshold."""
    results: list[AlignmentResult] = []
    for i, theme in enumerate(themes):
        if roadmap and sim.shape[1] > 0:
            j = int(np.argmax(sim[i]))
            best = float(sim[i][j])
            aligned = best >= threshold
            results.append(
                AlignmentResult(
                    theme_id=theme.theme_id,
                    roadmap_item_id=roadmap[j].item_id if aligned else None,
                    similarity=round(best, 4),
                    aligned=aligned,
                    alignment_reason=(
                        f"'{theme.name}' matches '{roadmap[j].title}' (sim {best:.2f})"
                        if aligned
                        else ""
                    ),
                )
            )
        else:
            results.append(AlignmentResult(theme_id=theme.theme_id, aligned=False))
    return results


class MappingAgent:
    def __init__(self, threshold: float = 0.75) -> None:
        self.threshold = threshold

    def map(self, themes: list[Theme], roadmap: list[RoadmapItem]) -> list[AlignmentResult]:
        if not themes:
            return []
        theme_emb = embed_texts([f"{t.name}. {t.description}" for t in themes])
        road_emb = embed_texts([f"{r.title}. {r.description}" for r in roadmap])
        sim = cosine_matrix(theme_emb, road_emb)
        return align_from_matrix(themes, roadmap, sim, self.threshold)
