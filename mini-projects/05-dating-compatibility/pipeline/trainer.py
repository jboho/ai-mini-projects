"""Fine-tune all-MiniLM-L6-v2 with CosineSimilarityLoss on the dating pairs.

CosineSimilarityLoss maps label 1 -> similarity 1.0 and label 0 -> 0.0, pulling
compatible profile embeddings together and pushing incompatible ones apart.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .models import DatingPair

logger = logging.getLogger(__name__)

BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def train_model(
    train_pairs: list[DatingPair],
    output_path: str | Path,
    base_model: str = BASE_MODEL,
    epochs: int = 4,
    batch_size: int = 16,
    warmup_steps: int = 100,
    device: str | None = None,
) -> Path:
    from sentence_transformers import InputExample, SentenceTransformer, losses
    from torch.utils.data import DataLoader

    device = device or os.environ.get("EMBED_DEVICE", "cpu")
    output_path = Path(output_path)
    logger.info(
        "Fine-tuning %s on %d pairs (%d epochs, batch %d, %s)",
        base_model,
        len(train_pairs),
        epochs,
        batch_size,
        device,
    )

    model = SentenceTransformer(base_model, device=device)
    examples = [InputExample(texts=[p.text_1, p.text_2], label=float(p.label)) for p in train_pairs]
    loader = DataLoader(examples, shuffle=True, batch_size=batch_size)
    train_loss = losses.CosineSimilarityLoss(model)

    model.fit(
        train_objectives=[(loader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        output_path=str(output_path),
        show_progress_bar=True,
    )
    logger.info("Saved fine-tuned model to %s", output_path)
    return output_path
