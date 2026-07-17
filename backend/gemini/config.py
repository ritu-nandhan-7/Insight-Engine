"""Configuration for the Gemini client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .constants import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL_NAME,
    DEFAULT_RETRY_BASE_DELAY_SECONDS,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    ENV_GEMINI_API_KEY,
    ENV_GEMINI_MODEL,
)
from .exceptions import GeminiConfigurationError


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Generation parameters sent to Gemini.

    All values are optional — None means the SDK default is used.
    """

    temperature: float | None = DEFAULT_TEMPERATURE
    max_output_tokens: int | None = DEFAULT_MAX_OUTPUT_TOKENS
    top_p: float | None = DEFAULT_TOP_P
    top_k: int | None = DEFAULT_TOP_K


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Retry behaviour for transient Gemini failures."""

    max_attempts: int = DEFAULT_RETRY_MAX_ATTEMPTS
    base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS


@dataclass(frozen=True, slots=True)
class GeminiClientConfig:
    """Immutable configuration for the Gemini client.

    The API key is read from an environment variable by default.
    The model name is also configurable via environment or constructor.
    """

    api_key: str
    model_name: str = DEFAULT_MODEL_NAME
    generation: GenerationConfig = GenerationConfig()
    retry: RetryConfig = RetryConfig()

    @classmethod
    def from_env(
        cls,
        generation: GenerationConfig | None = None,
        retry: RetryConfig | None = None,
        dotenv_path: str | Path | None = None,
    ) -> GeminiClientConfig:
        """Build configuration from environment variables.

        Automatically loads a .env file from the project root if present.

        Args:
            generation: Optional generation config overrides.
            retry: Optional retry config overrides.
            dotenv_path: Optional explicit path to .env file. If None, searches
                parent directories for a .env file.

        Reads:
            GEMINI_API_KEY — required
            GEMINI_MODEL  — optional, defaults to gemini-2.5-flash

        Raises:
            GeminiConfigurationError: If GEMINI_API_KEY is not set.
        """
        load_dotenv(dotenv_path=dotenv_path)

        api_key = os.environ.get(ENV_GEMINI_API_KEY)
        if not api_key:
            raise GeminiConfigurationError(
                f"Environment variable '{ENV_GEMINI_API_KEY}' is not set. "
                "Set it to your Gemini API key or pass api_key directly."
            )

        model_name = os.environ.get(ENV_GEMINI_MODEL, DEFAULT_MODEL_NAME)

        return cls(
            api_key=api_key,
            model_name=model_name,
            generation=generation or GenerationConfig(),
            retry=retry or RetryConfig(),
        )