"""Data models for the prompt builder package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.profiler import DatasetProfile


@dataclass(frozen=True, slots=True)
class SerializedColumn:
    """Compact representation of a single column for Gemini context."""

    name: str
    dtype: str
    semantic_type: str
    min: float | int | None = None
    max: float | int | None = None
    mean: float | None = None
    earliest: str | None = None
    latest: str | None = None
    top_values: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SerializedDataset:
    """Compact dataset context for the LLM prompt."""

    rows: int
    columns: int
    column_info: tuple[SerializedColumn, ...]


@dataclass(frozen=True, slots=True)
class PromptRequest:
    """Immutable prompt request ready for Gemini.

    Each component is kept separate — never merged into one string.
    """

    system_prompt: str
    dataset_context: SerializedDataset
    user_query: str
    metadata: dict[str, Any] = field(default_factory=dict)