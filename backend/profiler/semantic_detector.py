"""Structural semantic type detection for dataset columns."""

from __future__ import annotations

import re
from typing import Callable

import pandas as pd

from .constants import (
    CATEGORICAL_RATIO_THRESHOLD,
    SEMANTIC_CONFIDENCE_THRESHOLD,
    SEMANTIC_TYPE_BOOLEAN,
    SEMANTIC_TYPE_CATEGORICAL,
    SEMANTIC_TYPE_DATETIME,
    SEMANTIC_TYPE_ID,
    SEMANTIC_TYPE_NUMERIC,
    SEMANTIC_TYPE_TEXT,
    SEMANTIC_TYPE_UNKNOWN,
)


class SemanticDetector:
    """Infer structural semantic types using deterministic pandas dtype checks.

    Detection priority:
    1. ID (column name only)
    2. Datetime (pandas datetime64 dtype)
    3. Boolean (pandas bool dtype or boolean-like values)
    4. Numeric (pandas numeric dtype)
    5. Categorical (string/object with low cardinality)
    6. Text (remaining string/object columns)
    7. Unknown (fallback)
    """

    _ID_NAME_TOKENS = {
        "id", "uuid", "guid", "customer_id", "order_id", "product_id",
        "invoice_id", "employee_id", "user_id", "account_id", "transaction_id",
    }
    _BOOLEAN_VALUES = {"true", "false", "1", "0", "yes", "no", "y", "n", "t", "f"}

    def detect(self, column_name: str, series: pd.Series) -> str:
        """Infer a structural semantic type for a column."""

        normalized_name = column_name.strip().lower()

        # 1. ID detection by name only
        if self._is_id_name(normalized_name):
            return SEMANTIC_TYPE_ID

        # 2. Datetime detection (pandas datetime64 dtype or conservative string parsing)
        if pd.api.types.is_datetime64_any_dtype(series):
            return SEMANTIC_TYPE_DATETIME
        if self._is_datetime_like(series):
            return SEMANTIC_TYPE_DATETIME

        # 3. Boolean detection
        if pd.api.types.is_bool_dtype(series):
            return SEMANTIC_TYPE_BOOLEAN
        if self._is_boolean_like(series):
            return SEMANTIC_TYPE_BOOLEAN

        # 4. Numeric detection (pandas numeric dtype only)
        if pd.api.types.is_numeric_dtype(series):
            return SEMANTIC_TYPE_NUMERIC

        # 5. Categorical detection (string/object with low cardinality)
        if (series.dtype == object or pd.api.types.is_string_dtype(series)) and self._is_categorical(series):
            return SEMANTIC_TYPE_CATEGORICAL

        # 6. Text detection (remaining string/object columns)
        if series.dtype == object or pd.api.types.is_string_dtype(series):
            return SEMANTIC_TYPE_TEXT

        # 7. Unknown fallback
        return SEMANTIC_TYPE_UNKNOWN

    def _is_id_name(self, normalized_name: str) -> bool:
        """Check if column name suggests an ID column."""

        tokens = set(re.split(r"[^a-z0-9]+", normalized_name))
        return bool(tokens & self._ID_NAME_TOKENS)

    def _is_boolean_like(self, series: pd.Series) -> bool:
        """Check if non-null values are boolean-like."""

        values = series.dropna().astype("string").str.strip().str.lower()
        if values.empty:
            return False
        return values.isin(self._BOOLEAN_VALUES).mean() >= 0.9

    def _is_datetime_like(self, series: pd.Series) -> bool:
        """Check if string/object column parses as datetime with high confidence."""

        if pd.api.types.is_numeric_dtype(series):
            return False
        values = series.dropna().astype("string")
        if values.empty:
            return False
        parsed = pd.to_datetime(values, errors="coerce", utc=True)
        return parsed.notna().mean() >= SEMANTIC_CONFIDENCE_THRESHOLD

    def _is_categorical(self, series: pd.Series) -> bool:
        """Check if column has low cardinality (categorical)."""

        total_count = len(series)
        if total_count == 0:
            return False
        unique_count = series.nunique(dropna=True)
        cardinality_ratio = unique_count / total_count
        return cardinality_ratio <= CATEGORICAL_RATIO_THRESHOLD
