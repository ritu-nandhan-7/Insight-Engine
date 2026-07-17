"""Compact dataset serializer for LLM context."""

from __future__ import annotations

import logging
from datetime import datetime

from backend.profiler import (
    CategoricalColumnProfile,
    ColumnProfile,
    DatasetProfile,
    DatetimeColumnProfile,
    NumericColumnProfile,
)

from .constants import MAX_TOP_VALUES_IN_CONTEXT
from .exceptions import SerializationError
from .models import SerializedColumn, SerializedDataset

logger = logging.getLogger(__name__)


class DatasetSerializer:
    """Serialize DatasetProfile into a compact LLM-friendly representation.

    Extracts only the information Gemini needs to generate analysis code.
    Omits warnings, memory usage, timestamps, duplicate counts, and loading
    metadata to minimise token consumption.
    """

    def serialize(self, profile: DatasetProfile) -> SerializedDataset:
        """Convert a DatasetProfile into a compact SerializedDataset."""

        logger.info("Serializing profile")

        try:
            column_info = tuple(self._serialize_column(col) for col in profile.column_profiles)
        except Exception as exc:
            raise SerializationError(f"Failed to serialize dataset profile: {exc}") from exc

        return SerializedDataset(rows=profile.rows, columns=profile.columns, column_info=column_info)

    def _serialize_column(self, col: ColumnProfile) -> SerializedColumn:
        """Serialize a single column into its compact form."""

        result = SerializedColumn(
            name=col.name,
            dtype=col.pandas_dtype,
            semantic_type=col.inferred_semantic_type,
        )

        result = self._attach_numeric(result, col.numeric_profile)
        result = self._attach_datetime(result, col.datetime_profile)
        result = self._attach_categorical(result, col.categorical_profile)

        return result

    def _attach_numeric(
        self,
        column: SerializedColumn,
        numeric: NumericColumnProfile | None,
    ) -> SerializedColumn:
        if numeric is None:
            return column

        return SerializedColumn(
            name=column.name,
            dtype=column.dtype,
            semantic_type=column.semantic_type,
            min=numeric.minimum,
            max=numeric.maximum,
            mean=numeric.mean,
            earliest=column.earliest,
            latest=column.latest,
            top_values=column.top_values,
        )

    def _attach_datetime(
        self,
        column: SerializedColumn,
        datetime_profile: DatetimeColumnProfile | None,
    ) -> SerializedColumn:
        if datetime_profile is None:
            return column

        earliest = self._format_datetime(datetime_profile.earliest_date)
        latest = self._format_datetime(datetime_profile.latest_date)

        return SerializedColumn(
            name=column.name,
            dtype=column.dtype,
            semantic_type=column.semantic_type,
            min=column.min,
            max=column.max,
            mean=column.mean,
            earliest=earliest,
            latest=latest,
            top_values=column.top_values,
        )

    def _attach_categorical(
        self,
        column: SerializedColumn,
        categorical: CategoricalColumnProfile | None,
    ) -> SerializedColumn:
        if categorical is None or not categorical.top_values:
            return column

        top_values = tuple(
            str(tv.value) for tv in categorical.top_values[:MAX_TOP_VALUES_IN_CONTEXT]
        )

        return SerializedColumn(
            name=column.name,
            dtype=column.dtype,
            semantic_type=column.semantic_type,
            min=column.min,
            max=column.max,
            mean=column.mean,
            earliest=column.earliest,
            latest=column.latest,
            top_values=top_values,
        )

    @staticmethod
    def _format_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()