"""Data models for the code validator package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidatedCode:
    """Result of validating generated Python code."""

    python_code: str
    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)