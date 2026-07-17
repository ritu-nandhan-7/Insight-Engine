"""Dataset loading logic for Insight Engine."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .constants import SUPPORTED_DATASET_EXTENSIONS
from .exceptions import (
    CorruptedDatasetError,
    DatasetLoadError,
    EmptyDatasetError,
    UnsupportedFileTypeError,
)
from .models import LoadedDataset

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _DatasetSource:
    """Internal representation of a user-uploaded dataset source."""

    target: Any
    filename: str
    extension: str
    file_size_bytes: int


class _DatasetLoadLogger:
    """Encapsulates loader logging so loading code stays easy to extend."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def dataset_received(self, filename: str) -> None:
        self._logger.info("Dataset upload received: %s", filename)

    def loading_started(self, extension: str, filename: str) -> None:
        self._logger.info("Loading %s dataset: %s", extension.upper().lstrip("."), filename)

    def unsupported_format(self, extension: str, filename: str) -> None:
        self._logger.warning("Unsupported dataset format: %s (%s)", filename, extension or "unknown")

    def loading_failed(self, filename: str) -> None:
        self._logger.error("Dataset loading failed: %s", filename, exc_info=True)

    def loaded_successfully(self, filename: str, row_count: int, column_count: int) -> None:
        self._logger.info("Dataset loaded successfully: %s", filename)
        self._logger.info("Rows: %s", row_count)
        self._logger.info("Columns: %s", column_count)


class DatasetLoader:
    """Load user-uploaded datasets into memory.

    The loader is intentionally limited to a single responsibility: converting
    an uploaded file into a LoadedDataset object containing a pandas DataFrame
    and basic file-level details.
    """

    def __init__(self) -> None:
        self._events = _DatasetLoadLogger(logger)
        self._loaders: dict[str, Callable[[Any], pd.DataFrame]] = {
            ".csv": self._load_csv,
            ".xls": self._load_excel,
            ".xlsx": self._load_excel,
            ".json": self._load_json,
            ".parquet": self._load_parquet,
        }

    def load(self, file: Any) -> LoadedDataset:
        """Load an uploaded file into memory.

        Args:
            file: A file upload, file-like object, or file path.

        Returns:
            A LoadedDataset instance containing the loaded DataFrame and file metadata.

        Raises:
            UnsupportedFileTypeError: If the file extension is not supported.
            DatasetLoadError: If the file cannot be read.
            CorruptedDatasetError: If the file exists but cannot be parsed.
            EmptyDatasetError: If the resulting DataFrame has no rows.
        """

        source = self._build_source(file)
        self._events.dataset_received(source.filename)

        loader = self._loaders.get(source.extension)
        if loader is None:
            self._events.unsupported_format(source.extension, source.filename)
            raise UnsupportedFileTypeError(
                f"Unsupported dataset file type '{source.extension}'. Supported types are: "
                f"{', '.join(SUPPORTED_DATASET_EXTENSIONS)}"
            )

        try:
            self._events.loading_started(source.extension, source.filename)
            self._rewind_target(source.target)
            dataframe = loader(source.target)
        except (ValueError, pd.errors.ParserError, OSError, KeyError, TypeError) as exc:
            self._events.loading_failed(source.filename)
            raise CorruptedDatasetError(f"Failed to parse dataset '{source.filename}': {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._events.loading_failed(source.filename)
            raise DatasetLoadError(f"Failed to load dataset '{source.filename}': {exc}") from exc

        self._validate_dataframe(dataframe, source.filename)
        loaded_dataset = self._build_loaded_dataset(dataframe, source)
        self._events.loaded_successfully(
            loaded_dataset.filename,
            loaded_dataset.row_count,
            loaded_dataset.column_count,
        )
        return loaded_dataset

    def _build_source(self, file: Any) -> _DatasetSource:
        filename = self._resolve_filename(file)
        extension = self._resolve_extension(filename)
        file_size_bytes = self._resolve_file_size(file)
        target = self._resolve_target(file)

        return _DatasetSource(
            target=target,
            filename=filename,
            extension=extension,
            file_size_bytes=file_size_bytes,
        )

    def _resolve_target(self, file: Any) -> Any:
        if hasattr(file, "file") and hasattr(file, "filename"):
            return file.file
        return file

    def _resolve_filename(self, file: Any) -> str:
        if hasattr(file, "filename") and getattr(file, "filename"):
            return str(getattr(file, "filename"))

        if isinstance(file, (str, os.PathLike)):
            return Path(file).name

        if hasattr(file, "name") and getattr(file, "name"):
            return Path(str(getattr(file, "name"))).name

        raise DatasetLoadError("Could not determine the uploaded filename.")

    def _resolve_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if not extension:
            raise UnsupportedFileTypeError(
                f"Uploaded file '{filename}' does not have a supported extension. "
                f"Supported types are: {', '.join(SUPPORTED_DATASET_EXTENSIONS)}"
            )
        return extension

    def _resolve_file_size(self, file: Any) -> int:
        if hasattr(file, "size") and isinstance(getattr(file, "size"), int):
            return int(getattr(file, "size"))

        if isinstance(file, (str, os.PathLike)):
            return os.path.getsize(file)

        stream = getattr(file, "file", file)
        if hasattr(stream, "seek") and hasattr(stream, "tell"):
            current_position = stream.tell()
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(current_position)
            return int(size)

        raise DatasetLoadError("Could not determine the uploaded file size.")

    def _rewind_target(self, target: Any) -> None:
        if hasattr(target, "seek"):
            target.seek(0)

    def _load_csv(self, target: Any) -> pd.DataFrame:
        try:
            return pd.read_csv(target)
        except UnicodeDecodeError:
            # Fallback to common encodings for non-UTF-8 files
            import io

            if hasattr(target, "read"):
                raw = target.read()
                target.seek(0)
            else:
                with open(target, "rb") as f:
                    raw = f.read()

            for enc in ("latin1", "ISO-8859-1", "cp1252", "utf-16"):
                try:
                    decoded = raw.decode(enc)
                    return pd.read_csv(io.StringIO(decoded))
                except (UnicodeDecodeError, UnicodeError):
                    continue
            raise

    def _load_excel(self, target: Any) -> pd.DataFrame:
        return pd.read_excel(target)

    def _load_json(self, target: Any) -> pd.DataFrame:
        return pd.read_json(target)

    def _load_parquet(self, target: Any) -> pd.DataFrame:
        return pd.read_parquet(target)

    def _validate_dataframe(self, dataframe: pd.DataFrame, filename: str) -> None:
        if dataframe.empty:
            raise EmptyDatasetError(f"Dataset '{filename}' is empty.")

    def _build_loaded_dataset(self, dataframe: pd.DataFrame, source: _DatasetSource) -> LoadedDataset:
        row_count, column_count = dataframe.shape
        return LoadedDataset(
            dataframe=dataframe,
            filename=source.filename,
            extension=source.extension,
            file_size_bytes=source.file_size_bytes,
            row_count=row_count,
            column_count=column_count,
        )
