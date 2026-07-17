"""Constants for the correction engine package."""

from __future__ import annotations

MAX_CORRECTION_ATTEMPTS = 3

CORRECTION_INSTRUCTION = (
    "The previous code failed during execution with the following error:\n"
    "{error_message}\n\n"
    "Fix the Python code to resolve this issue.\n"
    "Do not change the user's original request.\n"
    "Return only valid JSON using the existing response contract."
)