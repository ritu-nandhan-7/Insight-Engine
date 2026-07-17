"""Prompt Builder — converts DatasetProfile + user query into a PromptRequest."""

from __future__ import annotations

import logging

from backend.profiler import DatasetProfile

from .exceptions import EmptyQueryError, MissingDatasetProfileError
from .models import PromptRequest
from .serializer import DatasetSerializer
from .templates import SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class _BuilderLogger:
    """Keeps builder logging separate from builder logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def building_started(self) -> None:
        self._logger.info("Prompt building started")

    def serializing_profile(self) -> None:
        self._logger.info("Serializing profile")

    def prompt_ready(self) -> None:
        self._logger.info("Prompt ready")


class PromptBuilder:
    """Build a PromptRequest from a DatasetProfile and a user query.

    The builder:
    1. Validates inputs.
    2. Serializes the DatasetProfile into a compact LLM-friendly form.
    3. Assembles the PromptRequest with system prompt, dataset context,
       and user query kept as separate components.
    """

    def __init__(self) -> None:
        self._events = _BuilderLogger(logger)
        self._serializer = DatasetSerializer()

    def build(self, profile: DatasetProfile, query: str) -> PromptRequest:
        """Build a PromptRequest from a DatasetProfile and user query.

        Args:
            profile: The privacy-safe dataset profile.
            query: The user's natural language question.

        Returns:
            A PromptRequest with separate system_prompt, dataset_context,
            and user_query fields.

        Raises:
            MissingDatasetProfileError: If profile is None.
            EmptyQueryError: If query is empty or whitespace-only.
        """
        self._events.building_started()

        if profile is None:
            raise MissingDatasetProfileError("A DatasetProfile is required to build a prompt.")

        stripped_query = query.strip() if query else ""
        if not stripped_query:
            raise EmptyQueryError("User query must not be empty.")

        self._events.serializing_profile()
        dataset_context = self._serializer.serialize(profile)

        prompt_request = PromptRequest(
            system_prompt=SYSTEM_PROMPT_TEMPLATE,
            dataset_context=dataset_context,
            user_query=stripped_query,
        )

        self._events.prompt_ready()
        return prompt_request