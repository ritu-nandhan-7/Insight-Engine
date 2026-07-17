"""Constants for the response parser package."""

from __future__ import annotations

VALID_STATUS_SUCCESS = "success"
VALID_STATUS_CLARIFICATION = "clarification"
VALID_STATUS_ERROR = "error"

VALID_STATUS_VALUES = {
    VALID_STATUS_SUCCESS,
    VALID_STATUS_CLARIFICATION,
    VALID_STATUS_ERROR,
}

REQUIRED_FIELDS_BY_STATUS: dict[str, set[str]] = {
    VALID_STATUS_SUCCESS: {"status", "title", "python"},
    VALID_STATUS_CLARIFICATION: {"status", "message"},
    VALID_STATUS_ERROR: {"status", "message"},
}