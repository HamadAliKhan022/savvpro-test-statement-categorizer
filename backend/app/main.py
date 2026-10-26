"""StatementIQ FastAPI application entrypoint."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def cors_origins() -> list[str]:
    """Comma-separated CORS_ORIGINS, so deploys need no code changes."""
    configured = os.getenv("CORS_ORIGINS")
    if not configured:
        return DEFAULT_ORIGINS
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app = FastAPI(
    title="StatementIQ API",
    description=(
        "Automated tax statement categorization for freelancers and small "
        "businesses. Categorization is performed by a deterministic rule "
        "engine - no LLMs or ML models are used."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"name": "StatementIQ", "docs": "/docs", "health": "/api/health"}
