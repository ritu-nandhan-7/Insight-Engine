"""Custom exceptions for the code validator package."""


class ValidationError(Exception):
    """Base class for all validation failures."""


class SyntaxValidationError(ValidationError):
    """Raised when the generated code has invalid Python syntax."""


class ForbiddenImportError(ValidationError):
    """Raised when the generated code contains forbidden import statements."""


class ForbiddenFunctionError(ValidationError):
    """Raised when the generated code calls forbidden built-in functions."""


class ForbiddenModuleError(ValidationError):
    """Raised when the generated code references forbidden module names."""


class MissingFigureError(ValidationError):
    """Raised when the generated code does not assign a figure to the required output variable."""