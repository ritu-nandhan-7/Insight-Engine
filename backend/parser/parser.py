"""Response parser for Gemini API responses."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from backend.gemini import RawGeminiResponse

from .constants import (
    REQUIRED_FIELDS_BY_STATUS,
    VALID_STATUS_CLARIFICATION,
    VALID_STATUS_ERROR,
    VALID_STATUS_SUCCESS,
    VALID_STATUS_VALUES,
)
from .exceptions import InvalidJsonError, InvalidStatusError, MissingFieldError, ResponseParsingError
from .models import ClarificationResponse, ErrorResponse, ParsedGeminiResponse, SuccessResponse

logger = logging.getLogger(__name__)


class _ParserLogger:
    """Keeps parser logging separate from parsing logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def parsing_started(self) -> None:
        self._logger.info("Response parsing started")

    def json_extracted(self, json_str: str) -> None:
        self._logger.info("JSON extracted")

    def json_validated(self) -> None:
        self._logger.info("JSON validated")

    def response_parsed(self, status: str) -> None:
        self._logger.info("Response parsed successfully (status=%s)", status)


class GeminiResponseParser:
    """Parse raw Gemini responses into strongly typed objects.

    Handles:
    - Pure JSON
    - Markdown-wrapped JSON
    - Extra explanatory text before/after JSON
    - Whitespace variations
    """

    def __init__(self) -> None:
        self._events = _ParserLogger(logger)

    def parse(self, raw_response: RawGeminiResponse) -> ParsedGeminiResponse:
        """Parse a RawGeminiResponse into a ParsedGeminiResponse.

        Args:
            raw_response: The raw response from the Gemini client.

        Returns:
            A validated ParsedGeminiResponse with typed fields.

        Raises:
            InvalidJsonError: If the response does not contain valid JSON.
            InvalidStatusError: If the status field is not recognised.
            MissingFieldError: If required fields are missing for the status.
        """
        self._events.parsing_started()

        json_str = self._extract_json(raw_response.raw_text)
        self._events.json_extracted(json_str)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise InvalidJsonError(f"Response is not valid JSON: {exc}") from exc

        self._events.json_validated()

        if not isinstance(data, dict):
            raise InvalidJsonError("Response must be a JSON object")

        status = data.get("status")
        if status not in VALID_STATUS_VALUES:
            raise InvalidStatusError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUS_VALUES))}"
            )

        required_fields = REQUIRED_FIELDS_BY_STATUS[status]
        missing = required_fields - set(data.keys())
        if missing:
            raise MissingFieldError(
                f"Missing required fields for status '{status}': {', '.join(sorted(missing))}"
            )

        if status == VALID_STATUS_SUCCESS:
            parsed = ParsedGeminiResponse(
                status=status,
                success=SuccessResponse(title=data["title"], python=data["python"]),
                raw_text=raw_response.raw_text,
            )
        elif status == VALID_STATUS_CLARIFICATION:
            parsed = ParsedGeminiResponse(
                status=status,
                clarification=ClarificationResponse(message=data["message"]),
                raw_text=raw_response.raw_text,
            )
        else:  # VALID_STATUS_ERROR
            parsed = ParsedGeminiResponse(
                status=status,
                error=ErrorResponse(message=data["message"]),
                raw_text=raw_response.raw_text,
            )

        self._events.response_parsed(status)
        return parsed

    def _extract_json(self, raw_text: str) -> str:
        """Extract the JSON payload from raw Gemini text.

        Handles:
        - Pure JSON: `{...}`
        - Markdown code blocks: ` ```json\n{...}\n``` `
        - Extra text before/after JSON
        - Leading/trailing whitespace
        """

        text = raw_text.strip()

        # Try markdown code block first
        markdown_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if markdown_match:
            return markdown_match.group(1).strip()

        # Try to find the first balanced JSON object
        start = text.find("{")
        if start == -1:
            raise InvalidJsonError("No JSON object found in response")

        # Find matching closing brace
        brace_count = 0
        for i in range(start, len(text)):
            char = text[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_str = text[start : i + 1]
                    return json_str.strip()

        raise InvalidJsonError("Unbalanced braces in JSON response")