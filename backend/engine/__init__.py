"""Insight Engine facade package."""

from .engine import InsightEngine
from .exceptions import EngineError, NoActiveDatasetError
from .models import DatasetSummary, EngineResult

__all__ = [
    "EngineError",
    "EngineResult",
    "DatasetSummary",
    "InsightEngine",
    "NoActiveDatasetError",
]