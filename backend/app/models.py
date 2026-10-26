"""Pydantic schemas for the StatementIQ API."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class OverrideRequest(BaseModel):
    category: str = Field(min_length=1, max_length=80)


class HealthResponse(BaseModel):
    status: str
    engine: str
    llm_used: bool = False


class CategoriesResponse(BaseModel):
    categories: List[str]
