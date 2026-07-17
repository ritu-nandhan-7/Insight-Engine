"""Column and dataset analyzers for the profiler package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .constants import (
    BOOLEAN_CONFIDENCE_THRESHOLD,
    CATEGORICAL_RATIO_THRESHOLD,
    HIGH_CARDINALITY_RATIO_THRESHOLD,
    HIGH_MISSING_PERCENTAGE_THRESHOLD,
    MAX_FREQUENCY_INFERENCE_UNIQUE_VALUES,
    MAX_TOP_VALUES,
    SEMANTIC_CONFIDENCE_THRESHOLD,
    SEMANTIC_TYPE_BOOLEAN,
    SEMANTIC_TYPE_CATEGORICAL,
    SEMANTIC_TYPE_DATETIME,
    SEMANTIC_TYPE_ID,
    SEMANTIC_TYPE_NUMERIC,
    SEMANTIC_TYPE_TEXT,
    SEMANTIC_TYPE_UNKNOWN,
    TEXT_LENGTH_MAXIMUM,
    TEXT_LENGTH_MINIMUM,
    VERY_HIGH_CARDINALITY_RATIO_THRESHOLD,
    VERY_HIGH_MISSING_PERCENTAGE_THRESHOLD,
    ROLE_DATETIME,
    ROLE_DIMENSION,
    ROLE_FLAG,
    ROLE_MEASURE,
    ROLE_TEXT,
    ROLE_UNKNOWN,
)
from .models import (
    BooleanColumnProfile,
    CategoricalColumnProfile,
    ColumnProfile,
    DatasetQualityProfile,
    DatasetWarning,
    DatetimeColumnProfile,
    NumericColumnProfile,
    TextColumnProfile,
    TopValueProfile,
)
from .semantic_detector import SemanticDetector


@dataclass(frozen=True, slots=True)
class ColumnAnalysisContext:
    """Reusable per-column state to avoid repeated scans."""

    series: pd.Series
    non_null: pd.Series
    null_count: int
    total_count: int
    unique_count: int
    duplicate_count: int
    null_percentage: float
    memory_usage_bytes: int
    nullable: bool
    is_constant: bool
    sample_as_string: pd.Series
    numeric_series: Optional[pd.Series]
    datetime_series: Optional[pd.Series]


class ColumnAnalyzer:
    """Build a privacy-safe ColumnProfile for a single series."""

    def __init__(self, semantic_detector: SemanticDetector | None = None) -> None:
        self._semantic_detector = semantic_detector or SemanticDetector()

    def detect_semantic_type(self, column_name: str, series: pd.Series) -> str:
        """Detect the semantic type for a column using deterministic rules."""

        return self._semantic_detector.detect(column_name, series)

    def analyze(self, column_name: str, series: pd.Series, semantic_type: str | None = None) -> ColumnProfile:
        semantic_type = semantic_type or self.detect_semantic_type(column_name, series)
        context = self._build_context(series, semantic_type)
        inferred_role = self._infer_role(series, semantic_type, context)

        numeric_profile = self._analyze_numeric(context)
        categorical_profile = self._analyze_categorical(context) if numeric_profile is None else None
        datetime_profile = self._analyze_datetime(context) if numeric_profile is None and categorical_profile is None else None
        boolean_profile = (
            self._analyze_boolean(context)
            if numeric_profile is None and categorical_profile is None and datetime_profile is None
            else None
        )
        text_profile = (
            self._analyze_text(context)
            if numeric_profile is None and categorical_profile is None and datetime_profile is None and boolean_profile is None
            else None
        )

        return ColumnProfile(
            name=column_name,
            pandas_dtype=str(series.dtype),
            inferred_semantic_type=semantic_type,
            nullable=context.nullable,
            null_count=context.null_count,
            null_percentage=context.null_percentage,
            unique_count=context.unique_count,
            duplicate_count=context.duplicate_count,
            inferred_role=inferred_role,
            memory_usage_bytes=context.memory_usage_bytes,
            is_constant=context.is_constant,
            is_potential_key=self._is_potential_key(series, semantic_type, context),
            numeric_profile=numeric_profile,
            categorical_profile=categorical_profile,
            text_profile=text_profile,
            datetime_profile=datetime_profile,
            boolean_profile=boolean_profile,
        )

    def _build_context(self, series: pd.Series, semantic_type: str) -> ColumnAnalysisContext:
        non_null = series.dropna()
        total_count = len(series)
        null_count = int(series.isna().sum())
        unique_count = int(non_null.nunique(dropna=True))
        duplicate_count = int(max(len(non_null) - unique_count, 0))
        nullable = null_count > 0
        null_percentage = float(null_count / total_count * 100) if total_count else 0.0
        memory_usage_bytes = int(series.memory_usage(deep=True))
        is_constant = bool(total_count > 0 and unique_count <= 1)
        sample_as_string = non_null.astype("string")
        numeric_series = self._build_numeric_series(series, semantic_type)
        datetime_series = self._build_datetime_series(series, semantic_type)

        return ColumnAnalysisContext(
            series=series,
            non_null=non_null,
            null_count=null_count,
            total_count=total_count,
            unique_count=unique_count,
            duplicate_count=duplicate_count,
            null_percentage=null_percentage,
            memory_usage_bytes=memory_usage_bytes,
            nullable=nullable,
            is_constant=is_constant,
            sample_as_string=sample_as_string,
            numeric_series=numeric_series,
            datetime_series=datetime_series,
        )

    def _build_numeric_series(self, series: pd.Series, semantic_type: str) -> Optional[pd.Series]:
        if pd.api.types.is_numeric_dtype(series):
            return pd.to_numeric(series, errors="coerce")
        if semantic_type != SEMANTIC_TYPE_NUMERIC:
            return None

        values = series.dropna().astype("string")
        if values.empty:
            return None
        numeric = pd.to_numeric(values, errors="coerce")
        return numeric if not numeric.isna().all() else None

    def _build_datetime_series(self, series: pd.Series, semantic_type: str) -> Optional[pd.Series]:
        if pd.api.types.is_datetime64_any_dtype(series):
            return pd.to_datetime(series, errors="coerce", utc=True)
        if semantic_type != SEMANTIC_TYPE_DATETIME:
            return None
        return pd.to_datetime(series, errors="coerce", utc=True)

    def _infer_role(self, series: pd.Series, semantic_type: str, context: ColumnAnalysisContext) -> str:
        if semantic_type == SEMANTIC_TYPE_DATETIME or pd.api.types.is_datetime64_any_dtype(series):
            return ROLE_DATETIME
        if semantic_type == SEMANTIC_TYPE_NUMERIC or pd.api.types.is_numeric_dtype(series):
            return ROLE_MEASURE
        if semantic_type == SEMANTIC_TYPE_BOOLEAN or pd.api.types.is_bool_dtype(series) or self._looks_boolean_like(series):
            return ROLE_FLAG
        if semantic_type == SEMANTIC_TYPE_ID:
            return ROLE_DIMENSION
        if semantic_type == SEMANTIC_TYPE_CATEGORICAL or (
            context.total_count and context.unique_count / max(context.total_count, 1) <= CATEGORICAL_RATIO_THRESHOLD
        ):
            return ROLE_DIMENSION
        if semantic_type == SEMANTIC_TYPE_TEXT or pd.api.types.is_string_dtype(series) or series.dtype == object:
            return ROLE_TEXT
        return ROLE_UNKNOWN

    def _analyze_numeric(self, context: ColumnAnalysisContext) -> Optional[NumericColumnProfile]:
        series = context.numeric_series
        if series is None:
            return None

        values = series.dropna()
        if values.empty:
            return None

        quartiles = values.quantile([0.25, 0.5, 0.75])
        q1 = float(quartiles.loc[0.25])
        median = float(quartiles.loc[0.5])
        q3 = float(quartiles.loc[0.75])
        return NumericColumnProfile(
            minimum=float(values.min()),
            maximum=float(values.max()),
            mean=float(values.mean()),
            median=median,
            standard_deviation=float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            variance=float(values.var(ddof=1)) if len(values) > 1 else 0.0,
            first_quartile=q1,
            third_quartile=q3,
            interquartile_range=float(q3 - q1),
            skewness=float(values.skew()) if len(values) > 2 else 0.0,
            kurtosis=float(values.kurt()) if len(values) > 3 else 0.0,
            zero_count=int((values == 0).sum()),
            negative_count=int((values < 0).sum()),
        )

    def _analyze_categorical(self, context: ColumnAnalysisContext) -> Optional[CategoricalColumnProfile]:
        if not self._is_categorical_candidate(context.series, context.unique_count, context.total_count):
            return None

        values = context.non_null.astype("string")
        if values.empty:
            return None

        counts = values.value_counts(dropna=True)
        top_values = tuple(
            TopValueProfile(
                value=str(index),
                frequency=int(count),
                percentage=float(count / len(values) * 100),
            )
            for index, count in counts.head(MAX_TOP_VALUES).items()
        )
        cardinality = float(context.unique_count / max(context.total_count, 1) * 100)
        return CategoricalColumnProfile(unique_count=context.unique_count, cardinality=cardinality, top_values=top_values)

    def _analyze_text(self, context: ColumnAnalysisContext) -> Optional[TextColumnProfile]:
        values = context.sample_as_string
        if values.empty:
            return None

        lengths = values.str.len()
        empty_string_count = int((values == "").sum())
        whitespace_only_count = int(values.str.match(r"^\s+$", na=False).sum())
        return TextColumnProfile(
            average_string_length=float(lengths.mean()) if not lengths.empty else None,
            minimum_string_length=int(lengths.min()) if not lengths.empty else None,
            maximum_string_length=int(lengths.max()) if not lengths.empty else None,
            empty_string_count=empty_string_count,
            whitespace_only_count=whitespace_only_count,
            unique_count=context.unique_count,
        )

    def _analyze_datetime(self, context: ColumnAnalysisContext) -> Optional[DatetimeColumnProfile]:
        series = context.datetime_series
        if series is None:
            return None

        values = series.dropna()
        if values.empty:
            return None

        earliest = values.min()
        latest = values.max()
        earliest_dt = earliest.to_pydatetime() if hasattr(earliest, "to_pydatetime") else earliest
        latest_dt = latest.to_pydatetime() if hasattr(latest, "to_pydatetime") else latest
        return DatetimeColumnProfile(
            earliest_date=earliest_dt,
            latest_date=latest_dt,
            total_date_span=(latest_dt - earliest_dt) if earliest_dt and latest_dt else None,
            detected_frequency=self._detect_frequency(values),
            missing_percentage=context.null_percentage,
        )

    def _analyze_boolean(self, context: ColumnAnalysisContext) -> Optional[BooleanColumnProfile]:
        series = context.series
        if not pd.api.types.is_bool_dtype(series) and not self._looks_boolean_like(series):
            return None

        values = series.dropna().astype("string").str.lower()
        if values.empty:
            return BooleanColumnProfile(true_count=0, false_count=0, missing_count=context.null_count)

        true_mask = values.isin({"true", "1", "yes", "y", "t"})
        return BooleanColumnProfile(
            true_count=int(true_mask.sum()),
            false_count=int((~true_mask).sum()),
            missing_count=context.null_count,
        )

    def _looks_boolean_like(self, series: pd.Series) -> bool:
        values = series.dropna().astype("string").str.lower()
        if values.empty:
            return False
        return values.isin({"true", "false", "1", "0", "yes", "no", "y", "n", "t", "f"}).mean() >= BOOLEAN_CONFIDENCE_THRESHOLD

    def _is_potential_key(self, series: pd.Series, semantic_type: str, context: ColumnAnalysisContext) -> bool:
        if context.is_constant or context.total_count == 0:
            return False

        if semantic_type in {
            SEMANTIC_TYPE_BOOLEAN,
            SEMANTIC_TYPE_DATETIME,
            SEMANTIC_TYPE_NUMERIC,
            SEMANTIC_TYPE_ID,
        }:
            return False

        uniqueness_ratio = context.unique_count / context.total_count
        return uniqueness_ratio >= VERY_HIGH_CARDINALITY_RATIO_THRESHOLD

    def _is_categorical_candidate(self, series: pd.Series, unique_count: int, total_count: int) -> bool:
        if total_count == 0 or pd.api.types.is_bool_dtype(series):
            return False
        if pd.api.types.is_numeric_dtype(series):
            return unique_count / total_count <= CATEGORICAL_RATIO_THRESHOLD and unique_count <= MAX_FREQUENCY_INFERENCE_UNIQUE_VALUES
        if series.dtype == object or pd.api.types.is_string_dtype(series):
            return unique_count / total_count <= HIGH_CARDINALITY_RATIO_THRESHOLD
        return False

    def _detect_frequency(self, values: pd.Series) -> Optional[str]:
        if len(values) < 3:
            return None
        inferred = pd.infer_freq(values.sort_values())
        return inferred if inferred is not None else None


class DatasetQualityAnalyzer:
    """Compute objective dataset-level quality metrics."""

    def analyze(self, dataframe: pd.DataFrame, column_profiles: tuple[ColumnProfile, ...]) -> DatasetQualityProfile:
        duplicate_rows = int(dataframe.duplicated().sum())
        total_rows = len(dataframe)
        duplicate_percentage = float(duplicate_rows / total_rows * 100) if total_rows else 0.0
        missing_by_column = dataframe.isna().sum()
        total_missing_values = int(missing_by_column.sum())
        total_cells = int(dataframe.shape[0] * dataframe.shape[1])
        missing_percentage = float(total_missing_values / total_cells * 100) if total_cells else 0.0

        columns_with_missing_values = tuple(str(column) for column, count in missing_by_column.items() if int(count) > 0)
        completely_empty_columns = tuple(str(column) for column, count in missing_by_column.items() if total_rows and int(count) == total_rows)
        constant_columns = tuple(profile.name for profile in column_profiles if profile.is_constant)
        high_cardinality_columns = tuple(
            profile.name
            for profile in column_profiles
            if (profile.categorical_profile is not None or profile.text_profile is not None)
            and total_rows
            and (profile.unique_count / total_rows) >= HIGH_CARDINALITY_RATIO_THRESHOLD
        )
        potential_key_columns = tuple(profile.name for profile in column_profiles if profile.is_potential_key)

        return DatasetQualityProfile(
            duplicate_rows=duplicate_rows,
            duplicate_percentage=duplicate_percentage,
            total_missing_values=total_missing_values,
            missing_percentage=missing_percentage,
            columns_with_missing_values=columns_with_missing_values,
            completely_empty_columns=completely_empty_columns,
            constant_columns=constant_columns,
            high_cardinality_columns=high_cardinality_columns,
            potential_key_columns=potential_key_columns,
        )


class DatasetWarningAnalyzer:
    """Create objective warnings from profile metrics without recommendations."""

    def analyze(
        self,
        dataframe: pd.DataFrame,
        column_profiles: tuple[ColumnProfile, ...],
        quality_profile: DatasetQualityProfile,
    ) -> tuple[DatasetWarning, ...]:
        warnings: list[DatasetWarning] = []
        total_rows = len(dataframe)

        high_missing_columns = [profile.name for profile in column_profiles if profile.null_percentage >= HIGH_MISSING_PERCENTAGE_THRESHOLD]
        very_high_missing_columns = [profile.name for profile in column_profiles if profile.null_percentage >= VERY_HIGH_MISSING_PERCENTAGE_THRESHOLD]
        constant_columns = [profile.name for profile in column_profiles if profile.is_constant]
        potential_key_columns = [profile.name for profile in column_profiles if profile.is_potential_key]
        high_cardinality_columns = [
            profile.name
            for profile in column_profiles
            if (profile.categorical_profile is not None or profile.text_profile is not None)
            and total_rows
            and (profile.unique_count / total_rows) >= HIGH_CARDINALITY_RATIO_THRESHOLD
        ]

        if high_missing_columns:
            warnings.append(DatasetWarning(warning_type="high_missing_values", message=self._format_bullets("Columns with high missing values", high_missing_columns)))

        if very_high_missing_columns:
            warnings.append(DatasetWarning(warning_type="very_high_missing_values", message=self._format_bullets("Columns with very high missing values", very_high_missing_columns)))

        if constant_columns:
            warnings.append(DatasetWarning(warning_type="constant_columns", message=self._format_bullets("Constant columns", constant_columns)))

        if potential_key_columns:
            warnings.append(DatasetWarning(warning_type="potential_key_columns", message=self._format_bullets("Potential Key Columns", potential_key_columns)))

        if high_cardinality_columns:
            warnings.append(DatasetWarning(warning_type="high_cardinality_columns", message=self._format_bullets("High-cardinality columns", high_cardinality_columns)))

        if quality_profile.completely_empty_columns:
            warnings.append(DatasetWarning(warning_type="completely_empty_columns", message=self._format_bullets("Completely empty columns", list(quality_profile.completely_empty_columns))))

        return tuple(warnings)

    def _format_bullets(self, title: str, columns: list[str]) -> str:
        lines = [title]
        lines.extend(f"- {column}" for column in columns)
        return "\n".join(lines)
