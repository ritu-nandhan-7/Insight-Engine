"""Custom exceptions for the response parser package."""


class ResponseParsingError(Exception):
    """Base class for all response parsing failures."""


class InvalidJsonError(ResponseParsingError):
    """Raised when the Gemini response is not valid JSON."""


class InvalidStatusError(ResponseParsingError):
    """Raised when the status field is not a recognised value."""


class MissingFieldError(ResponseParsingError):
    """Raised when a required field is missing from the response."""