"""Data models for the correction engine package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.runtime.models import ExecutionResult


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    """Result of a correction attempt."""

    execution_result: ExecutionResult
    attempt_count: int
    corrected: bool
    metadata: dict[str, Any] = field(default_factory=dict)