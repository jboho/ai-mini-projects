"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import analytics, context, core, docs, issues, sprint, suggestions, write


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jira Copilot API",
        version="1.0.0",
        description="AI-powered Jira copilot over the TAWOS dataset.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (core, issues, context, suggestions, sprint, write, analytics, docs):
        app.include_router(module.router)
    return app


app = create_app()
