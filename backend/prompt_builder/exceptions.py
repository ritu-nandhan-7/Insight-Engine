"""Custom exceptions for the prompt builder package."""


class PromptBuilderError(Exception):
    """Base class for prompt builder failures."""


class MissingDatasetProfileError(PromptBuilderError):
    """Raised when no DatasetProfile is provided."""


class EmptyQueryError(PromptBuilderError):
    """Raised when the user query is empty or whitespace-only."""


class SerializationError(PromptBuilderError):
    """Raised when dataset profile serialization fails."""