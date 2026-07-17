"""Dataset profiling orchestration for Insight Engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

import pandas as pd

from backend.dataset import LoadedDataset

from .analyzers import ColumnAnalyzer, DatasetQualityAnalyzer, DatasetWarningAnalyzer
from .exceptions import DatasetProfilingError, InvalidLoadedDatasetError
from .models import ColumnProfile, DatasetProfile, DatasetQualityProfile, DatasetWarning
from .constants import (
    SEMANTIC_TYPE_BOOLEAN,
    SEMANTIC_TYPE_CATEGORICAL,
    SEMANTIC_TYPE_DATETIME,
    SEMANTIC_TYPE_ID,
    SEMANTIC_TYPE_NUMERIC,
    SEMANTIC_TYPE_TEXT,
    SEMANTIC_TYPE_UNKNOWN,
)

logger = logging.getLogger(__name__)


class _ProfilerLogger:
    """Keeps profiling logs separate from profiling logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def profiling_started(self, filename: str) -> None:
        self._logger.info("Data profiling started: %s", filename)

    def profiling_column(self, column_name: str) -> None:
        self._logger.info('Profiling column "%s"', column_name)

    def semantic_type_detected(self, column_name: str, semantic_type: str) -> None:
        self._logger.info('Detected semantic type for "%s": %s', column_name, semantic_type)

    def statistics_started(self, statistic_name: str, column_name: str) -> None:
        self._logger.info('Computing %s statistics for "%s"', statistic_name, column_name)

    def dataset_completed(self, filename: str, duration_ms: int) -> None:
        self._logger.info("Dataset profiling completed: %s (duration_ms=%s)", filename, duration_ms)

    def profiling_failed(self, filename: str) -> None:
        self._logger.error("Dataset profiling failed: %s", filename, exc_info=True)


@dataclass(slots=True)
class _DatasetValidationResult:
    """Validated dataset inputs used by the profiler."""

    dataset: LoadedDataset
    dataframe: pd.DataFrame


class DataProfiler:
    """Create a privacy-safe DatasetProfile from a LoadedDataset."""

    def __init__(self) -> None:
        self._events = _ProfilerLogger(logger)
        self._column_analyzer = ColumnAnalyzer()
        self._quality_analyzer = DatasetQualityAnalyzer()
        self._warning_analyzer = DatasetWarningAnalyzer()

    def profile(self, loaded_dataset: LoadedDataset) -> DatasetProfile:
        """Profile a loaded dataset without exposing raw rows."""

        validation = self._validate_input(loaded_dataset)
        started_at = perf_counter()
        self._events.profiling_started(validation.dataset.filename)

        try:
            column_profiles = self._analyze_columns(validation.dataframe)
            quality_profile = self._quality_analyzer.analyze(validation.dataframe, column_profiles)
            warnings = self._warning_analyzer.analyze(validation.dataframe, column_profiles, quality_profile)
            profile = self._build_profile(
                validation.dataset,
                validation.dataframe,
                column_profiles,
                quality_profile,
                warnings,
                started_at,
            )
            self._events.dataset_completed(validation.dataset.filename, profile.profile_duration_ms)
            return profile
        except DatasetProfilingError:
            self._events.profiling_failed(validation.dataset.filename)
            raise
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._events.profiling_failed(validation.dataset.filename)
            raise DatasetProfilingError(f"Failed to profile dataset '{validation.dataset.filename}': {exc}") from exc

    def _validate_input(self, loaded_dataset: LoadedDataset) -> _DatasetValidationResult:
        if not isinstance(loaded_dataset, LoadedDataset):
            raise InvalidLoadedDatasetError("DataProfiler expects a LoadedDataset instance.")
        if not isinstance(loaded_dataset.dataframe, pd.DataFrame):
            raise InvalidLoadedDatasetError("LoadedDataset.dataframe must be a pandas DataFrame.")
        return _DatasetValidationResult(dataset=loaded_dataset, dataframe=loaded_dataset.dataframe)

    def _analyze_columns(self, dataframe: pd.DataFrame) -> tuple[ColumnProfile, ...]:
        column_profiles: list[ColumnProfile] = []
        for column_name in dataframe.columns:
            column_name_str = str(column_name)
            self._events.profiling_column(column_name_str)
            semantic_type = self._column_analyzer.detect_semantic_type(column_name_str, dataframe[column_name])
            self._events.semantic_type_detected(column_name_str, semantic_type)
            statistics_label = self._statistic_label(semantic_type)
            if statistics_label is not None:
                self._events.statistics_started(statistics_label, column_name_str)
            column_profiles.append(self._column_analyzer.analyze(column_name_str, dataframe[column_name], semantic_type))
        return tuple(column_profiles)

    def _statistic_label(self, semantic_type: str) -> str | None:
        if semantic_type == SEMANTIC_TYPE_NUMERIC:
            return "numeric"
        if semantic_type == SEMANTIC_TYPE_DATETIME:
            return "datetime"
        return None

    def _build_profile(
        self,
        dataset: LoadedDataset,
        dataframe: pd.DataFrame,
        column_profiles: tuple[ColumnProfile, ...],
        quality_profile: DatasetQualityProfile,
        warnings: tuple[DatasetWarning, ...],
        started_at: float,
    ) -> DatasetProfile:
        memory_usage_bytes = int(dataframe.memory_usage(deep=True).sum())
        duration_ms = int((perf_counter() - started_at) * 1000)
        return DatasetProfile(
            dataset_id=dataset.dataset_id,
            filename=dataset.filename,
            rows=int(dataset.row_count),
            columns=int(dataset.column_count),
            memory_usage_bytes=memory_usage_bytes,
            file_size_bytes=int(dataset.file_size_bytes),
            profiled_at=datetime.now(timezone.utc),
            profile_duration_ms=duration_ms,
            column_profiles=column_profiles,
            quality_profile=quality_profile,
            warnings=warnings,
        )
