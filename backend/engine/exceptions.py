"""Custom exceptions for the Insight Engine facade."""


class EngineError(Exception):
    """Base class for all engine failures."""


class NoActiveDatasetError(EngineError):
    """Raised when an operation requires an active dataset but none is loaded."""