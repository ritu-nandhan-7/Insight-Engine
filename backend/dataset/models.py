"""Data models for dataset loading."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pandas as pd


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    """Represents a dataset loaded into memory.

    Attributes:
        dataset_id: Unique identifier for the loaded dataset.
        dataframe: The loaded pandas DataFrame.
        filename: The original uploaded filename.
        extension: The normalized file extension.
        file_size_bytes: File size in bytes.
        row_count: Number of rows in the DataFrame.
        column_count: Number of columns in the DataFrame.
        loaded_at: UTC timestamp when the dataset was loaded.
    """

    dataframe: pd.DataFrame
    filename: str
    extension: str
    file_size_bytes: int
    row_count: int
    column_count: int
    dataset_id: UUID = field(default_factory=uuid4, init=False)
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), init=False)
