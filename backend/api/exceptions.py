"""Centralized HTTP exceptions for the FastAPI API layer.

All endpoints raise these instead of constructing ``HTTPException`` inline so
that error responses stay consistent across the API.
"""

from fastapi import HTTPException, status


class NoActiveDatasetHTTPError(HTTPException):
    """Raised when no active dataset exists for the operation."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "detail": "No active dataset. Upload a dataset first."},
        )


class EngineHTTPError(HTTPException):
    """Raised when the engine encounters an error."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "detail": message},
        )