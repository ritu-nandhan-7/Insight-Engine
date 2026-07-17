"""Custom exceptions for the correction engine package."""


class CorrectionError(Exception):
    """Base class for all correction failures."""


class CorrectionAttemptsExceeded(CorrectionError):
    """Raised when maximum correction attempts have been reached."""