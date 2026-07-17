"""Custom exceptions for the Gemini client package."""


class GeminiError(Exception):
    """Base class for all Gemini client failures."""


class GeminiAuthenticationError(GeminiError):
    """Raised when the API key is invalid or missing."""


class GeminiRateLimitError(GeminiError):
    """Raised when the API rate limit is exceeded."""


class GeminiConnectionError(GeminiError):
    """Raised when a network or connection error occurs."""


class GeminiResponseError(GeminiError):
    """Raised when Gemini returns an unexpected or malformed response."""


class GeminiConfigurationError(GeminiError):
    """Raised when the client is misconfigured (e.g. missing API key)."""