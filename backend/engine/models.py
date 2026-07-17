"""Data models for the Insight Engine facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.profiler.models import DatasetProfile
from backend.runtime.models import ExecutionResult


@dataclass(frozen=True, slots=True)
class DatasetSummary:
    """Lightweight summary of the active dataset."""

    dataset_id: str
    filename: str
    rows: int
    columns: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineResult:
    """Result of an ask() operation."""

    execution_result: ExecutionResult
    corrected: bool
    attempt_count: int
    metadata: dict[str, Any] = field(default_factory=dict)