"""Core endpoints: chat, query, search, health."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...agents.crew import JiraCopilotCrew
from ...schemas.domain import ParsedQuery
from ...schemas.requests import ChatRequest, QueryRequest, SearchRequest
from ...schemas.responses import SearchResultItem
from ...services.vector_store import VectorStore
from ..deps import get_crew, get_vector_store

router = APIRouter(tags=["core"])


@router.get("/health")
def health(vector_store: VectorStore = Depends(get_vector_store)) -> dict:
    return {"status": "ok", "issues_indexed": vector_store.collection.count()}


@router.post("/chat")
def chat(req: ChatRequest, crew: JiraCopilotCrew = Depends(get_crew)) -> dict:
    return crew.chat(req.message)


@router.post("/query", response_model=ParsedQuery)
def query(req: QueryRequest, crew: JiraCopilotCrew = Depends(get_crew)) -> ParsedQuery:
    return crew.route(req.text)


@router.post("/search", response_model=list[SearchResultItem])
def search(req: SearchRequest, crew: JiraCopilotCrew = Depends(get_crew)) -> list[SearchResultItem]:
    return crew.search(req.query, filters=req.filters, limit=req.limit)
