"""Shared fixtures: sample emails, chunks, and a style profile."""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import pytest  # noqa: E402

from core.models import EmailMessage, KnowledgeChunk  # noqa: E402


@pytest.fixture
def sample_emails() -> list[EmailMessage]:
    return [
        EmailMessage(
            sender="vince.kaminski@enron.com",
            recipients=["team@enron.com"],
            subject="Re: model review",
            body="Hi team, Thanks for the update. I think we should review the model because "
            "the assumptions look off. However, the overall approach is sound. Best, Vince",
            folder="_sent_mail",
        ),
        EmailMessage(
            sender="vince.kaminski@enron.com",
            recipients=["john@enron.com"],
            subject="quick question",
            body="Hi John, Could you send me the latest numbers? Therefore we can finalize. "
            "Thanks!",
            folder="_sent_mail",
        ),
    ]


@pytest.fixture
def sample_chunks() -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(
            chunk_id="c0",
            content="A neural network learns weights via backprop.",
            source_field="computer science",
            chunk_index=0,
        ),
        KnowledgeChunk(
            chunk_id="c1",
            content="A hash table maps keys to buckets in O(1).",
            source_field="computer science",
            chunk_index=1,
        ),
        KnowledgeChunk(
            chunk_id="c2",
            content="Gradient descent minimizes a loss function.",
            source_field="computer science",
            chunk_index=2,
        ),
    ]
