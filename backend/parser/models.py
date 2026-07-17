"""Data models for the response parser package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SuccessResponse:
    """A successful Gemini response containing generated Python code."""

    title: str
    python: str


@dataclass(frozen=True, slots=True)
class ClarificationResponse:
    """Gemini needs more information from the user."""

    message: str


@dataclass(frozen=True, slots=True)
class ErrorResponse:
    """Gemini encountered an error processing the request."""

    message: str


@dataclass(frozen=True, slots=True)
class ParsedGeminiResponse:
    """Strongly typed, validated response from Gemini.

    Exactly one of success, clarification, or error will be set.
    """

    status: str
    success: SuccessResponse | None = None
    clarification: ClarificationResponse | None = None
    error: ErrorResponse | None = None
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)