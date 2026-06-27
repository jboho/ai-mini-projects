"""Query-time RAG pipeline: chunk -> embed -> index -> retrieve (-> rerank) -> answer.

Assembles the swappable components from a RunConfig over a set of documents and
exposes retrieve()/answer() for the CLI and Streamlit app.
"""

from __future__ import annotations

from .chunkers import get_chunker
from .config import RunConfig
from .embedder import embed_chunks, get_embedder
from .models import Document, QAResponse, RetrievalResult
from .rerankers import get_reranker
from .retrievers import get_retriever
from .vector_store import VectorStore


class RAGPipeline:
    def __init__(self, config: RunConfig, documents: list[Document]) -> None:
        self.config = config
        embedder = get_embedder(config.embedder)
        chunker = get_chunker(config.chunker, embedder=embedder)

        chunks = []
        for doc in documents:
            chunks.extend(chunker.chunk(doc))

        embeddings = embed_chunks(embedder, chunks, config.cache_key)
        store = VectorStore.from_embeddings(embeddings, chunks)
        self._chunk_by_id = {c.id: c for c in chunks}
        self.retriever = get_retriever(config.retriever, embedder, store, chunks)
        self.reranker = get_reranker(config.reranker)
        self.top_k = config.top_k
        self._generator = None

    def retrieve(self, question: str) -> list[RetrievalResult]:
        candidate_k = self.top_k if self.reranker is None else max(self.top_k * 3, 20)
        results = self.retriever.retrieve(question, candidate_k)
        if self.reranker is not None:
            return self.reranker.rerank(question, results, self.top_k)
        return results[: self.top_k]

    def answer(self, question: str) -> QAResponse:
        if self._generator is None:
            from .generator import get_generator

            self._generator = get_generator()
        results = self.retrieve(question)
        chunks = [self._chunk_by_id[r.chunk_id] for r in results]
        response = self._generator.generate(question, chunks)
        response.retrieved = results
        return response
