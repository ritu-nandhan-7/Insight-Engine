"""Data models for dataset profiling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import pandas as pd


@dataclass(frozen=True, slots=True)
class TopValueProfile:
    """Represents one aggregated categorical value."""

    value: str
    frequency: int
    percentage: float


@dataclass(frozen=True, slots=True)
class DatasetWarning:
    """Objective observation about dataset structure or quality."""

    warning_type: str
    message: str
    column_name: Optional[str] = None


@dataclass(frozen=True, slots=True)
class NumericColumnProfile:
    """Aggregated numeric statistics for a column."""

    minimum: Optional[float]
    maximum: Optional[float]
    mean: Optional[float]
    median: Optional[float]
    standard_deviation: Optional[float]
    variance: Optional[float]
    first_quartile: Optional[float]
    third_quartile: Optional[float]
    interquartile_range: Optional[float]
    skewness: Optional[float]
    kurtosis: Optional[float]
    zero_count: int
    negative_count: int


@dataclass(frozen=True, slots=True)
class CategoricalColumnProfile:
    """Aggregated categorical statistics for a column."""

    unique_count: int
    cardinality: float
    top_values: tuple[TopValueProfile, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TextColumnProfile:
    """Aggregated text statistics for a column."""

    average_string_length: Optional[float]
    minimum_string_length: Optional[int]
    maximum_string_length: Optional[int]
    empty_string_count: int
    whitespace_only_count: int
    unique_count: int


@dataclass(frozen=True, slots=True)
class DatetimeColumnProfile:
    """Aggregated datetime statistics for a column."""

    earliest_date: Optional[datetime]
    latest_date: Optional[datetime]
    total_date_span: Optional[timedelta]
    detected_frequency: Optional[str]
    missing_percentage: float


@dataclass(frozen=True, slots=True)
class BooleanColumnProfile:
    """Aggregated boolean statistics for a column."""

    true_count: int
    false_count: int
    missing_count: int


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """Comprehensive privacy-safe profile for a single column."""

    name: str
    pandas_dtype: str
    inferred_semantic_type: str
    nullable: bool
    null_count: int
    null_percentage: float
    unique_count: int
    duplicate_count: int
    inferred_role: str
    memory_usage_bytes: int
    is_constant: bool
    is_potential_key: bool
    numeric_profile: Optional[NumericColumnProfile] = None
    categorical_profile: Optional[CategoricalColumnProfile] = None
    text_profile: Optional[TextColumnProfile] = None
    datetime_profile: Optional[DatetimeColumnProfile] = None
    boolean_profile: Optional[BooleanColumnProfile] = None


@dataclass(frozen=True, slots=True)
class DatasetQualityProfile:
    """Objective quality metrics for the full dataset."""

    duplicate_rows: int
    duplicate_percentage: float
    total_missing_values: int
    missing_percentage: float
    columns_with_missing_values: tuple[str, ...]
    completely_empty_columns: tuple[str, ...]
    constant_columns: tuple[str, ...]
    high_cardinality_columns: tuple[str, ...]
    potential_key_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    """Privacy-safe structural profile for a loaded dataset."""

    dataset_id: UUID
    filename: str
    rows: int
    columns: int
    memory_usage_bytes: int
    file_size_bytes: int
    profiled_at: datetime
    profile_duration_ms: int
    column_profiles: tuple[ColumnProfile, ...]
    quality_profile: DatasetQualityProfile
    warnings: tuple[DatasetWarning, ...] = field(default_factory=tuple)
