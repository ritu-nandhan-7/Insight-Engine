"""Data models for the Gemini client package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class UsageInfo:
    """Token usage metadata from a Gemini response."""

    prompt_token_count: int | None = None
    response_token_count: int | None = None
    total_token_count: int | None = None


@dataclass(frozen=True, slots=True)
class RawGeminiResponse:
    """Raw response from Gemini exactly as received.

    No parsing, no validation, no code inspection is performed.
    This is the untouched output of the API call.
    """

    raw_text: str
    model_name: str
    finish_reason: str | None = None
    response_id: str | None = None
    usage: UsageInfo | None = None
    metadata: dict[str, Any] = field(default_factory=dict)