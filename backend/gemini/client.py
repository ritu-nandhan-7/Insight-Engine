"""Gemini API client for Insight Engine."""

from __future__ import annotations

import json
import logging
import time

from google.genai import Client as GenAiClient
from google.genai import errors as genai_errors
from google.genai import types

from backend.prompt_builder import PromptRequest

from .config import GeminiClientConfig
from .exceptions import (
    GeminiAuthenticationError,
    GeminiConnectionError,
    GeminiRateLimitError,
    GeminiResponseError,
)
from .models import RawGeminiResponse, UsageInfo

logger = logging.getLogger(__name__)


class _ClientLogger:
    """Keeps client logging separate from client logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def preparing_request(self) -> None:
        self._logger.info("Preparing Gemini request")

    def sending_request(self, model_name: str) -> None:
        self._logger.info('Sending request to Gemini (model="%s")', model_name)

    def response_received(self) -> None:
        self._logger.info("Gemini response received")

    def retrying(self, attempt: int, max_attempts: int, delay: float) -> None:
        self._logger.info(
            "Retrying Gemini request (attempt %d/%d, delay=%.1fs)",
            attempt,
            max_attempts,
            delay,
        )

    def request_completed(self, model_name: str, finish_reason: str | None) -> None:
        self._logger.info(
            'Gemini request completed (model="%s", finish_reason="%s")',
            model_name,
            finish_reason,
        )


class GeminiClient:
    """Communicates with the Gemini API.

    This client:
    - Accepts a PromptRequest (system_prompt + dataset_context + user_query).
    - Calls the Gemini API with the prepared contents.
    - Returns the raw response untouched.

    It has NO knowledge of datasets, profiling, execution, validation, or
    visualisation. It is purely an API communication layer.
    """

    def __init__(self, config: GeminiClientConfig | None = None) -> None:
        self._config = config or GeminiClientConfig.from_env()
        self._events = _ClientLogger(logger)
        self._client = self._build_client()

    def _build_client(self) -> GenAiClient:
        """Create the underlying Gemini SDK client."""

        return GenAiClient(api_key=self._config.api_key)

    def generate(self, prompt_request: PromptRequest) -> RawGeminiResponse:
        """Send a PromptRequest to Gemini and return the raw response.

        Args:
            prompt_request: A fully built PromptRequest with system_prompt,
                dataset_context, and user_query.

        Returns:
            A RawGeminiResponse containing the untouched Gemini output.

        Raises:
            GeminiAuthenticationError: If the API key is invalid.
            GeminiRateLimitError: If the rate limit is exceeded.
            GeminiConnectionError: If a network or connection error occurs.
            GeminiResponseError: If Gemini returns an unexpected response.
            GeminiConfigurationError: If the client is misconfigured.
        """
        self._events.preparing_request()

        system_instruction = self._build_system_instruction(prompt_request)
        contents = self._build_contents(prompt_request)

        self._events.sending_request(self._config.model_name)

        response = self._call_with_retry(system_instruction, contents)
        self._events.request_completed(
            self._config.model_name,
            self._extract_finish_reason(response),
        )

        return self._to_raw_response(response)

    def _build_system_instruction(self, prompt_request: PromptRequest) -> str:
        """Extract the system prompt from the PromptRequest."""

        return prompt_request.system_prompt

    def _build_contents(self, prompt_request: PromptRequest) -> str:
        """Build the user message contents from the PromptRequest.

        The serialized dataset context is converted to JSON and combined
        with the user query. The PromptRequest components are not modified.
        """

        context = prompt_request.dataset_context

        # Serialize the dataset context manually to keep control over formatting
        serialized_columns = []
        for col in context.column_info:
            col_dict = {"name": col.name, "dtype": col.dtype, "semantic_type": col.semantic_type}
            if col.min is not None:
                col_dict["min"] = col.min
            if col.max is not None:
                col_dict["max"] = col.max
            if col.mean is not None:
                col_dict["mean"] = col.mean
            if col.earliest is not None:
                col_dict["earliest"] = col.earliest
            if col.latest is not None:
                col_dict["latest"] = col.latest
            if col.top_values:
                col_dict["top_values"] = list(col.top_values)
            serialized_columns.append(col_dict)

        context_payload = {
            "rows": context.rows,
            "columns": context.columns,
            "column_info": serialized_columns,
        }

        context_json_str = json.dumps(context_payload, indent=2, default=str)

        return f"Dataset Context:\n{context_json_str}\n\nUser Question:\n{prompt_request.user_query}"

    def _call_with_retry(self, system_instruction: str, contents: str) -> types.GenerateContentResponse:
        """Call Gemini with retry logic for transient failures."""

        config = self._config
        retry_config = config.retry
        generation = config.generation

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=generation.temperature,
            max_output_tokens=generation.max_output_tokens,
            top_p=generation.top_p,
            top_k=generation.top_k,
        )

        last_exception: Exception | None = None

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model=config.model_name,
                    contents=contents,
                    config=gen_config,
                )
                self._events.response_received()
                return response

            except genai_errors.ClientError as exc:
                # 4xx errors — only retry on ratelimit (429)
                status_code = getattr(exc, "code", 0) or self._extract_status_code(exc)
                if status_code == 429:
                    if attempt < retry_config.max_attempts:
                        delay = retry_config.base_delay_seconds * (2 ** (attempt - 1))
                        self._events.retrying(attempt + 1, retry_config.max_attempts, delay)
                        time.sleep(delay)
                        last_exception = GeminiRateLimitError(
                            f"Rate limit exceeded (attempt {attempt}/{retry_config.max_attempts})"
                        )
                        continue
                    raise GeminiRateLimitError(
                        f"Rate limit exceeded after {retry_config.max_attempts} attempts"
                    ) from exc

                if status_code == 403 or status_code == 401:
                    raise GeminiAuthenticationError(
                        f"Authentication failed (status={status_code}). Check your API key."
                    ) from exc

                raise GeminiResponseError(
                    f"Gemini returned a client error (status={status_code}): {exc}"
                ) from exc

            except genai_errors.ServerError as exc:
                # 5xx errors — transient, retry
                if attempt < retry_config.max_attempts:
                    delay = retry_config.base_delay_seconds * (2 ** (attempt - 1))
                    self._events.retrying(attempt + 1, retry_config.max_attempts, delay)
                    time.sleep(delay)
                    last_exception = GeminiConnectionError(
                        f"Gemini server error (attempt {attempt}/{retry_config.max_attempts}): {exc}"
                    )
                    continue
                raise GeminiConnectionError(
                    f"Gemini server error after {retry_config.max_attempts} attempts: {exc}"
                ) from exc

            except genai_errors.APIError as exc:
                # Broad API errors — retry
                if attempt < retry_config.max_attempts:
                    delay = retry_config.base_delay_seconds * (2 ** (attempt - 1))
                    self._events.retrying(attempt + 1, retry_config.max_attempts, delay)
                    time.sleep(delay)
                    last_exception = GeminiConnectionError(
                        f"Gemini API error (attempt {attempt}/{retry_config.max_attempts}): {exc}"
                    )
                    continue
                raise GeminiConnectionError(
                    f"Gemini API error after {retry_config.max_attempts} attempts: {exc}"
                ) from exc

            except Exception as exc:
                raise GeminiConnectionError(f"Unexpected error during Gemini API call: {exc}") from exc

        # Should not reach here, but safeguard against edge cases
        raise GeminiConnectionError(
            f"Request failed after {retry_config.max_attempts} attempts"
        ) from last_exception

    def _to_raw_response(self, response: types.GenerateContentResponse) -> RawGeminiResponse:
        """Convert the SDK response into a RawGeminiResponse without parsing."""

        raw_text = response.text if response.text is not None else ""

        finish_reason = self._extract_finish_reason(response)

        usage = None
        if response.usage_metadata is not None:
            usage = UsageInfo(
                prompt_token_count=getattr(response.usage_metadata, "prompt_token_count", None),
                response_token_count=(
                    getattr(response.usage_metadata, "candidates_token_count", None)
                    or getattr(response.usage_metadata, "response_token_count", None)
                ),
                total_token_count=getattr(response.usage_metadata, "total_token_count", None),
            )

        return RawGeminiResponse(
            raw_text=raw_text,
            model_name=self._config.model_name,
            finish_reason=finish_reason,
            response_id=response.response_id,
            usage=usage,
        )

    @staticmethod
    def _extract_finish_reason(response: types.GenerateContentResponse) -> str | None:
        """Extract the finish reason string from the response."""

        if not response.candidates:
            return None
        candidate = response.candidates[0]
        if candidate.finish_reason is None:
            return None
        return candidate.finish_reason.value

    @staticmethod
    def _extract_status_code(exc: Exception) -> int:
        """Try to extract an HTTP status code from an exception."""

        import httpx

        if isinstance(exc, genai_errors.ClientError):
            # Try common patterns
            if hasattr(exc, "code"):
                return exc.code
            if hasattr(exc, "status_code"):
                return exc.status_code
        return 0