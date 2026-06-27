"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Resume-Job Pipeline API",
        version="1.0.0",
        description=(
            "Review resumes against job descriptions and retrieve failure analysis."
        ),
    )
    app.include_router(router)
    return app


app = create_app()
