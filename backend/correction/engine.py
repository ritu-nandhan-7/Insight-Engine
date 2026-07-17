"""Correction engine for automatic retry on execution failures."""

from __future__ import annotations

import logging
from typing import Any

from backend.dataset import LoadedDataset
from backend.gemini import GeminiClient, GeminiClientConfig
from backend.parser import GeminiResponseParser, SuccessResponse
from backend.profiler.models import DatasetProfile
from backend.prompt_builder import PromptBuilder
from backend.runtime import PythonRuntime, ExecutionResult
from backend.validator import CodeValidator, ValidatedCode

from .constants import CORRECTION_INSTRUCTION, MAX_CORRECTION_ATTEMPTS
from .exceptions import CorrectionAttemptsExceeded, CorrectionError
from .models import CorrectionResult

logger = logging.getLogger(__name__)


class _CorrectionLogger:
    """Keeps correction logging separate from orchestration logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def correction_started(self, attempt: int) -> None:
        self._logger.info("Correction started (attempt %d)", attempt)

    def retry_attempt(self, attempt: int) -> None:
        self._logger.info("Retry attempt %d", attempt)

    def correction_received(self) -> None:
        self._logger.info("Correction received")

    def validation_passed(self) -> None:
        self._logger.info("Validation passed")

    def execution_succeeded(self) -> None:
        self._logger.info("Execution succeeded")

    def max_retries_reached(self) -> None:
        self._logger.error("Maximum retries reached")


class CorrectionEngine:
    """Orchestrate automatic correction of failed code execution.

    The engine:
    - Receives the original pipeline inputs plus the execution error
    - Reuses existing modules (PromptBuilder, GeminiClient, etc.)
    - Retries up to MAX_CORRECTION_ATTEMPTS times
    - Returns CorrectionResult with final execution result
    """

    def __init__(
        self,
        gemini_config: GeminiClientConfig | None = None,
    ) -> None:
        self._events = _CorrectionLogger(logger)
        self._gemini_config = gemini_config
        self._prompt_builder = PromptBuilder()
        self._gemini_client: GeminiClient | None = None
        self._parser = GeminiResponseParser()
        self._validator = CodeValidator()
        self._runtime = PythonRuntime()

    def correct(
        self,
        dataset: LoadedDataset,
        profile: DatasetProfile,
        original_prompt_request: Any,
        original_response: SuccessResponse,
        original_validated: ValidatedCode,
        execution_error: Exception,
    ) -> CorrectionResult:
        """Attempt to correct failed code execution.

        Args:
            dataset: The loaded dataset.
            profile: The dataset profile.
            original_prompt_request: The original PromptRequest.
            original_response: The original SuccessResponse from Gemini.
            original_validated: The original ValidatedCode that failed.
            execution_error: The exception from the failed execution.

        Returns:
            CorrectionResult with the final execution result.

        Raises:
            CorrectionAttemptsExceeded: If all retry attempts fail.
        """
        self._events.correction_started(1)

        # Initialize Gemini client if needed
        if self._gemini_client is None:
            config = self._gemini_config or GeminiClientConfig.from_env()
            self._gemini_client = GeminiClient(config=config)

        attempt_count = 1
        last_error = execution_error

        for attempt in range(1, MAX_CORRECTION_ATTEMPTS + 1):
            if attempt > 1:
                self._events.retry_attempt(attempt)

            # Build correction prompt
            correction_prompt = self._build_correction_prompt(
                original_prompt_request=original_prompt_request,
                original_code=original_validated.python_code,
                error_message=str(last_error),
            )

            # Send correction to Gemini
            try:
                raw_response = self._gemini_client.generate(correction_prompt)
                self._events.correction_received()
            except Exception as exc:
                last_error = exc
                if attempt == MAX_CORRECTION_ATTEMPTS:
                    raise CorrectionAttemptsExceeded(
                        f"Correction attempt {attempt} failed: {exc}"
                    ) from exc
                continue

            # Parse response
            try:
                parsed = self._parser.parse(raw_response)
                if parsed.status != "success" or not parsed.success:
                    last_error = CorrectionError(
                        f"Gemini returned non-success status: {parsed.status}"
                    )
                    if attempt == MAX_CORRECTION_ATTEMPTS:
                        raise CorrectionAttemptsExceeded(
                            f"Correction attempt {attempt} returned non-success"
                        ) from last_error
                    continue
            except Exception as exc:
                last_error = exc
                if attempt == MAX_CORRECTION_ATTEMPTS:
                    raise CorrectionAttemptsExceeded(
                        f"Correction attempt {attempt} failed to parse response: {exc}"
                    ) from exc
                continue

            # Validate corrected code
            validated = self._validator.validate(parsed.success.python)
            if not validated.is_valid:
                last_error = CorrectionError(
                    f"Corrected code failed validation: {validated.errors[0]}"
                )
                if attempt == MAX_CORRECTION_ATTEMPTS:
                    raise CorrectionAttemptsExceeded(
                        f"Correction attempt {attempt} produced invalid code"
                    ) from last_error
                continue

            self._events.validation_passed()

            # Execute corrected code
            try:
                result = self._runtime.execute(dataset, validated)
                self._events.execution_succeeded()
                return CorrectionResult(
                    execution_result=result,
                    attempt_count=attempt,
                    corrected=(attempt > 1),
                )
            except Exception as exc:
                last_error = exc
                if attempt == MAX_CORRECTION_ATTEMPTS:
                    raise CorrectionAttemptsExceeded(
                        f"All {MAX_CORRECTION_ATTEMPTS} correction attempts failed"
                    ) from last_error
                continue

        # Should not reach here, but safeguard
        self._events.max_retries_reached()
        raise CorrectionAttemptsExceeded(
            f"All {MAX_CORRECTION_ATTEMPTS} correction attempts failed"
        ) from last_error

    def _build_correction_prompt(
        self,
        original_prompt_request: Any,
        original_code: str,
        error_message: str,
    ) -> Any:
        """Build a correction prompt request.

        Reuses the original prompt request but appends correction context.
        """

        from backend.prompt_builder.models import PromptRequest

        # Build correction instruction
        correction_text = CORRECTION_INSTRUCTION.format(error_message=error_message)

        # Append correction to original user query
        corrected_query = (
            f"{original_prompt_request.user_query}\n\n"
            f"[CORRECTION REQUEST]\n{correction_text}"
        )

        # Build new prompt request with same context but corrected query
        return PromptRequest(
            system_prompt=original_prompt_request.system_prompt,
            dataset_context=original_prompt_request.dataset_context,
            user_query=corrected_query,
        )