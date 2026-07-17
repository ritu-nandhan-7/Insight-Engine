"""Constants for the Gemini client package."""

from __future__ import annotations

# Environment variable names
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
ENV_GEMINI_MODEL = "GEMINI_MODEL"

# Default model name
DEFAULT_MODEL_NAME = "gemini-flash-lite-latest"

# Generation config defaults
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_TOP_P = 0.95
DEFAULT_TOP_K = 32

# Retry defaults
DEFAULT_RETRY_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BASE_DELAY_SECONDS = 1.0

# HTTP status codes for transient failures
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}