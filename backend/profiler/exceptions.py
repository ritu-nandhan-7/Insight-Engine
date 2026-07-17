"""Custom exceptions for the dataset profiler package."""


class ProfilerError(Exception):
    """Base class for profiler failures."""


class InvalidLoadedDatasetError(ProfilerError):
    """Raised when the profiler receives an invalid LoadedDataset object."""


class DatasetProfilingError(ProfilerError):
    """Raised when dataset profiling cannot be completed."""
