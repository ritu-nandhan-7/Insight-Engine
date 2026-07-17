"""Pydantic schemas for the FastAPI API layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    query: str


class DatasetSummaryResponse(BaseModel):
    """Response for dataset summary endpoints."""

    filename: str
    rows: int
    columns: int
    file_size_bytes: int
    memory_usage_bytes: int
    profile_duration_ms: int


class EngineResultResponse(BaseModel):
    """Consistent success response for the /query endpoint."""

    status: str = "success"
    title: str
    execution_time_ms: float
    figure: dict[str, Any]
    query: str
    timestamp: float


class DataPreviewResponse(BaseModel):
    """Response for dataset data preview."""

    columns: list[str]
    rows: list[list[str | int | float | bool | None]]
    total_rows: int


class HealthResponse(BaseModel):
    """Response for the /health endpoint."""

    status: str = "ok"
