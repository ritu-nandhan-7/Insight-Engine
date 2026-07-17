"""FastAPI routes for the Insight Engine API.

Every endpoint communicates ONLY with the InsightEngine facade. No internal
modules are accessed directly.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile

from fastapi import APIRouter, File, UploadFile, Request, status

from backend.engine import InsightEngine, NoActiveDatasetError

from .dependencies import get_or_create_session
from .exceptions import EngineHTTPError, NoActiveDatasetHTTPError
from .schemas import DataPreviewResponse, DatasetSummaryResponse, EngineResultResponse, HealthResponse, QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""

    return HealthResponse()


@router.post("/upload", response_model=DatasetSummaryResponse)
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> DatasetSummaryResponse:
    """Upload and profile a dataset, replacing any active session."""

    engine = get_or_create_session(request)

    original_filename = file.filename or "dataset.csv"
    suffix = os.path.splitext(original_filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        summary = engine.upload_dataset(tmp_path)
    except Exception as exc:
        raise EngineHTTPError(str(exc)) from exc
    finally:
        os.unlink(tmp_path)

    logger.info("Dataset uploaded via API: %s", summary.filename)
    return DatasetSummaryResponse(
        filename=original_filename,
        rows=summary.rows,
        columns=summary.columns,
        file_size_bytes=summary.metadata.get("file_size_bytes", 0),
        memory_usage_bytes=summary.metadata.get("memory_usage_bytes", 0),
        profile_duration_ms=summary.metadata.get("profile_duration_ms", 0),
    )


@router.post("/query", response_model=EngineResultResponse)
def query(request: Request, body: QueryRequest) -> EngineResultResponse:
    """Process a user query against the active dataset."""

    engine = get_or_create_session(request)

    try:
        result = engine.ask(body.query)
    except NoActiveDatasetError as exc:
        raise NoActiveDatasetHTTPError() from exc
    except Exception as exc:
        raise EngineHTTPError(str(exc)) from exc

    figure = result.execution_result.figure
    title = figure.layout.title.text if figure.layout.title.text else "Chart"

    return EngineResultResponse(
        title=title,
        execution_time_ms=result.execution_result.execution_time_ms,
        figure=json.loads(figure.to_json()),
        query=body.query,
        timestamp=__import__("time").time(),
    )


@router.get("/dataset", response_model=DatasetSummaryResponse)
def get_dataset(request: Request) -> DatasetSummaryResponse:
    """Get the active dataset summary."""

    engine = get_or_create_session(request)

    try:
        summary = engine.get_dataset_summary()
    except NoActiveDatasetError as exc:
        raise NoActiveDatasetHTTPError() from exc

    return DatasetSummaryResponse(
        filename=summary.filename,
        rows=summary.rows,
        columns=summary.columns,
        file_size_bytes=summary.metadata.get("file_size_bytes", 0),
        memory_usage_bytes=summary.metadata.get("memory_usage_bytes", 0),
        profile_duration_ms=summary.metadata.get("profile_duration_ms", 0),
    )


@router.get("/dataset/preview", response_model=DataPreviewResponse)
def dataset_preview(request: Request) -> DataPreviewResponse:
    """Get the top 5 rows of the active dataset."""

    engine = get_or_create_session(request)

    try:
        preview = engine.get_dataset_preview()
    except NoActiveDatasetError as exc:
        raise NoActiveDatasetHTTPError() from exc

    return DataPreviewResponse(
        columns=preview["columns"],
        rows=preview["rows"],
        total_rows=preview["total_rows"],
    )


@router.delete("/dataset", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def clear_dataset(request: Request) -> None:
    """Clear the active dataset session."""

    engine = get_or_create_session(request)
    engine.clear_session()
    logger.info("Session cleared via API")
