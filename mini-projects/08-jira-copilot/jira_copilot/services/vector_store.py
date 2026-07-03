"""Vector store: ChromaDB semantic search + BM25 keyword search + hybrid fusion.

Pure scoring/text helpers (``tokenize``, ``build_issue_content``, ``normalize_scores``,
``fuse_scores``) are kept module-level so they are unit-testable without ChromaDB or
any network access. The embedder is pluggable: a deterministic ``StubEmbedder`` keeps
the test suite fully offline, while ``OpenAIEmbedder`` is used for real seeding.
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from typing import Protocol

import chromadb
from chromadb.api.types import EmbeddingFunction

from ..config import get_settings
from ..db.models import Issue

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NULL_INT = -1  # ChromaDB metadata rejects None; sentinel for missing FK ids


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def build_issue_content(issue: Issue) -> str:
    """Document text used for embedding + BM25 (key + title + truncated description)."""
    content = f"{issue.issue_key} {issue.title}".strip()
    if issue.description_text:
        content += f" {issue.description_text[:2000]}"
    return content


def issue_metadata(issue: Issue) -> dict:
    """ChromaDB-safe metadata (str/int/float/bool only) for filtered search."""
    project_key = issue.project.key if issue.project else ""
    components = ",".join(c.name for c in issue.components) if issue.components else ""
    return {
        "type": issue.type or "",
        "status": issue.status or "",
        "priority": issue.priority or "",
        "project": project_key,
        "sprint_id": issue.sprint_id if issue.sprint_id is not None else _NULL_INT,
        "assignee_id": issue.assignee_id if issue.assignee_id is not None else _NULL_INT,
        "components": components,
        "title": issue.title or "",
    }


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalize to [0, 1]. Uniform inputs collapse to 1.0 (all equally ranked)."""
    if not scores:
        return {}
    vals = scores.values()
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def fuse_scores(
    semantic: dict[str, float],
    keyword: dict[str, float],
    alpha: float = 0.7,
) -> list[tuple[str, float]]:
    """Combine normalized semantic + keyword scores: ``alpha*sem + (1-alpha)*kw``."""
    sn = normalize_scores(semantic)
    kn = normalize_scores(keyword)
    fused = [
        (key, alpha * sn.get(key, 0.0) + (1.0 - alpha) * kn.get(key, 0.0))
        for key in set(sn) | set(kn)
    ]
    fused.sort(key=lambda kv: kv[1], reverse=True)
    return fused


def _stable_hash(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode()).digest()[:4], "big")


def _matches_filters(meta: dict, filters: dict | None) -> bool:
    if not filters:
        return True
    return all(meta.get(field) == value for field, value in filters.items())


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class StubEmbedder:
    """Deterministic hashed bag-of-words embeddings. Offline, no model download.

    Overlapping vocabulary yields higher cosine similarity, which is enough for the
    test suite to assert relevance ordering without a real embedding model.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in tokenize(text):
                vec[_stable_hash(token) % self.dim] += 1.0
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            out.append([x / norm for x in vec])
        return out


class OpenAIEmbedder:
    """Embeddings via the OpenAI API (``text-embedding-3-small`` by default)."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        settings = get_settings()
        self.model = model or settings.embedding_model
        kwargs: dict = {"api_key": api_key or settings.openai_api_key or None}
        resolved_base = base_url or settings.openai_base_url
        if resolved_base:
            kwargs["base_url"] = resolved_base
        self.client = OpenAI(**kwargs)

    def embed(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t if t.strip() else " " for t in texts]
        resp = self.client.embeddings.create(model=self.model, input=cleaned)
        return [item.embedding for item in resp.data]


class _ChromaEmbeddingFunction(EmbeddingFunction):
    """Adapts our ``Embedder`` to ChromaDB's EmbeddingFunction interface.

    We always pass precomputed embeddings to add/query, so this is rarely invoked, but
    supplying it prevents ChromaDB from falling back to its onnx default model (which
    triggers a download and OpenMP issues on macOS).
    """

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or StubEmbedder()

    def __call__(self, input):  # noqa: A002 - name fixed by ChromaDB interface
        return self._embedder.embed(list(input))

    @staticmethod
    def name() -> str:
        return "jira-copilot-embedder"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "_ChromaEmbeddingFunction":
        return _ChromaEmbeddingFunction()


def _default_embedder() -> Embedder:
    """OpenAI when a key is configured, otherwise the offline stub."""
    if get_settings().openai_api_key:
        return OpenAIEmbedder()
    return StubEmbedder()


class VectorStore:
    """Hybrid search over a ChromaDB collection.

    Semantic search uses ChromaDB cosine similarity over precomputed embeddings.
    Keyword search uses an in-memory BM25 index rebuilt from the collection's
    documents (cheap at this scale; survives a persistent reload).
    """

    def __init__(self, collection, embedder: Embedder) -> None:
        self.collection = collection
        self.embedder = embedder
        self._ids: list[str] = []
        self._docs: list[str] = []
        self._metas: list[dict] = []
        self._bm25 = None
        self._refresh_corpus()

    def index_issues(self, issues: list[Issue], batch_size: int = 128) -> int:
        contents = [build_issue_content(i) for i in issues]
        metadatas = [issue_metadata(i) for i in issues]
        ids = [i.issue_key for i in issues]
        count = 0
        for start in range(0, len(issues), batch_size):
            sl = slice(start, start + batch_size)
            batch_ids = ids[sl]
            if not batch_ids:
                continue
            embeddings = self.embedder.embed(contents[sl])
            self.collection.upsert(
                ids=batch_ids,
                embeddings=embeddings,
                documents=contents[sl],
                metadatas=metadatas[sl],
            )
            count += len(batch_ids)
        self._refresh_corpus()
        return count

    def _refresh_corpus(self) -> None:
        from rank_bm25 import BM25Okapi

        data = self.collection.get(include=["documents", "metadatas"])
        self._ids = data.get("ids") or []
        self._docs = data.get("documents") or []
        self._metas = data.get("metadatas") or []
        tokenized = [tokenize(doc) for doc in self._docs]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def semantic_search(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[dict]:
        if self.collection.count() == 0:
            return []
        embedding = self.embedder.embed([query])[0]
        res = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(limit, self.collection.count()),
            where=filters or None,
            include=["documents", "metadatas", "distances"],
        )
        out: list[dict] = []
        for key, doc, meta, dist in zip(
            res["ids"][0],
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):
            out.append({"key": key, "score": 1.0 - dist, "document": doc, "metadata": meta})
        return out

    def keyword_search(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 10,
    ) -> list[dict]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(self._ids)), key=lambda idx: scores[idx], reverse=True)
        out: list[dict] = []
        for idx in ranked:
            if scores[idx] <= 0:
                break
            if not _matches_filters(self._metas[idx], filters):
                continue
            out.append(
                {
                    "key": self._ids[idx],
                    "score": float(scores[idx]),
                    "document": self._docs[idx],
                    "metadata": self._metas[idx],
                }
            )
            if len(out) >= limit:
                break
        return out

    def hybrid_search(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 10,
        alpha: float = 0.7,
    ) -> list[dict]:
        pool = max(limit * 4, 20)
        semantic = self.semantic_search(query, filters, pool)
        keyword = self.keyword_search(query, filters, pool)
        records = {r["key"]: r for r in keyword}
        records.update({r["key"]: r for r in semantic})  # prefer semantic doc/meta
        sem_scores = {r["key"]: r["score"] for r in semantic}
        kw_scores = {r["key"]: r["score"] for r in keyword}
        out: list[dict] = []
        for key, combined in fuse_scores(sem_scores, kw_scores, alpha)[:limit]:
            record = records[key]
            out.append(
                {
                    "key": key,
                    "score": combined,
                    "semantic_score": sem_scores.get(key, 0.0),
                    "keyword_score": kw_scores.get(key, 0.0),
                    "document": record["document"],
                    "metadata": record["metadata"],
                }
            )
        return out


def make_vector_store(
    persist_path: str | None = None,
    embedder: Embedder | None = None,
    collection_name: str = "issues",
) -> VectorStore:
    embedder = embedder or _default_embedder()
    if persist_path:
        client = chromadb.PersistentClient(path=persist_path)
    else:
        # EphemeralClient shares a process-global system, so a fixed collection name
        # would leak (and clash on embedding dim) across stores. Use a unique name.
        client = chromadb.EphemeralClient()
        collection_name = f"{collection_name}_{uuid.uuid4().hex[:12]}"
    collection = client.get_or_create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=_ChromaEmbeddingFunction(embedder),
    )
    return VectorStore(collection, embedder)
