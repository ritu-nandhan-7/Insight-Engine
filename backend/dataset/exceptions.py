"""Custom exceptions for dataset loading."""


class DatasetError(Exception):
    """Base class for dataset loading errors."""


class UnsupportedFileTypeError(DatasetError):
    """Raised when the uploaded file extension is not supported."""


class DatasetLoadError(DatasetError):
    """Raised when a dataset cannot be loaded."""


class EmptyDatasetError(DatasetError):
    """Raised when a loaded dataset contains no rows."""


class CorruptedDatasetError(DatasetError):
    """Raised when the dataset file cannot be parsed reliably."""
