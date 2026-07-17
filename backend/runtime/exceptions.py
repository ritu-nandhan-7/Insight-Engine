"""Custom exceptions for the Python runtime package."""


class ExecutionError(Exception):
    """Base class for all execution failures."""


class RuntimeExecutionError(ExecutionError):
    """Raised when Python code execution fails at runtime."""


class FigureNotFoundError(ExecutionError):
    """Raised when the executed code does not produce a figure."""