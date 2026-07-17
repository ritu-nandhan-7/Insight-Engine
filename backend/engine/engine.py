"""Insight Engine facade - single entry point for the AI Core pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.dataset import DatasetLoader, LoadedDataset
from backend.profiler import DataProfiler
from backend.prompt_builder import PromptBuilder
from backend.gemini import (
    GeminiClient,
    GeminiClientConfig,
    GenerationConfig,
    RetryConfig,
)
from backend.parser import GeminiResponseParser, SuccessResponse
from backend.validator import CodeValidator, ValidatedCode
from backend.runtime import PythonRuntime, ExecutionResult
from backend.correction import CorrectionEngine, CorrectionResult

from .constants import DEFAULT_GEMINI_MODEL
from .exceptions import EngineError, NoActiveDatasetError
from .models import DatasetSummary, EngineResult

logger = logging.getLogger(__name__)


class _EngineLogger:
    """Keeps engine logging separate from orchestration logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def dataset_uploaded(self, filename: str) -> None:
        self._logger.info("Dataset uploaded: %s", filename)

    def dataset_profiled(self, filename: str, duration_ms: int) -> None:
        self._logger.info("Dataset profiled: %s (duration_ms=%s)", filename, duration_ms)

    def query_received(self, query: str) -> None:
        self._logger.info("Query received: %s", query)

    def execution_started(self) -> None:
        self._logger.info("Execution started")

    def execution_completed(self, duration_ms: int) -> None:
        self._logger.info("Execution completed (duration_ms=%s)", duration_ms)

    def session_cleared(self) -> None:
        self._logger.info("Session cleared")


class InsightEngine:
    """Single entry point for the Insight Engine AI Core pipeline.

    The engine:
    - Owns one instance of each AI Core module
    - Manages an active dataset session in memory
    - Orchestrates the complete pipeline: load → profile → prompt → generate → parse → validate → execute → correct
    - Provides a simple public API for external modules (FastAPI, CLI, React, etc.)

    Usage:
        engine = InsightEngine()
        engine.upload_dataset("data.csv")
        result = engine.ask("Show top 10 products by sales")
        engine.clear_session()
    """

    def __init__(self, gemini_api_key: str | None = None) -> None:
        """Initialize the Insight Engine.

        Args:
            gemini_api_key: Optional Gemini API key. If not provided, loads from environment.
        """
        self._events = _EngineLogger(logger)
        self._loader = DatasetLoader()
        self._profiler = DataProfiler()
        self._prompt_builder = PromptBuilder()
        self._parser = GeminiResponseParser()
        self._validator = CodeValidator()
        self._runtime = PythonRuntime()
        self._correction_engine = CorrectionEngine()

        # Active dataset session
        self._active_dataset: LoadedDataset | None = None
        self._active_profile: Any = None  # DatasetProfile

        # Initialize Gemini client
        config = self._build_gemini_config(gemini_api_key)
        self._gemini_client = GeminiClient(config=config)

    def _build_gemini_config(self, api_key: str | None) -> Any:
        """Build Gemini client configuration."""

        from backend.gemini import GeminiClientConfig, GenerationConfig, RetryConfig

        if api_key:
            return GeminiClientConfig(
                api_key=api_key,
                model_name=DEFAULT_GEMINI_MODEL,
                generation=GenerationConfig(temperature=0.2, max_output_tokens=4096),
                retry=RetryConfig(max_attempts=5, base_delay_seconds=2.0),
            )

        return GeminiClientConfig.from_env(
            generation=GenerationConfig(temperature=0.2, max_output_tokens=4096),
            retry=RetryConfig(max_attempts=5, base_delay_seconds=2.0),
        )

    def upload_dataset(self, file_path: str | Path) -> DatasetSummary:
        """Load and profile a dataset, storing it as the active session.

        Args:
            file_path: Path to the dataset file (CSV, Excel, etc.)

        Returns:
            DatasetSummary with lightweight information about the loaded dataset.

        Raises:
            EngineError: If dataset loading or profiling fails.
        """
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise EngineError(f"Dataset file not found: {path}")

        # Load dataset
        loaded = self._loader.load(path)
        self._events.dataset_uploaded(loaded.filename)

        # Profile dataset
        profile = self._profiler.profile(loaded)
        self._events.dataset_profiled(loaded.filename, profile.profile_duration_ms)

        # Store as active session
        self._active_dataset = loaded
        self._active_profile = profile

        return self._build_dataset_summary(loaded)

    def ask(self, user_query: str) -> EngineResult:
        """Process a user query against the active dataset.

        Args:
            user_query: Natural language question or visualization request.

        Returns:
            EngineResult containing the execution result and metadata.

        Raises:
            NoActiveDatasetError: If no dataset has been uploaded.
            EngineError: If the pipeline fails.
        """
        if self._active_dataset is None or self._active_profile is None:
            raise NoActiveDatasetError("No active dataset. Call upload_dataset() first.")

        self._events.query_received(user_query)

        # Build prompt
        prompt_request = self._prompt_builder.build(self._active_profile, user_query)

        # Generate code with Gemini
        raw_response = self._gemini_client.generate(prompt_request)

        # Parse response
        parsed = self._parser.parse(raw_response)

        if parsed.status != "success" or not parsed.success:
            raise EngineError(f"Gemini returned non-success status: {parsed.status}")

        # Validate code
        validated = self._validator.validate(parsed.success.python)
        if not validated.is_valid:
            raise EngineError(f"Generated code failed validation: {validated.errors[0]}")

        # Execute code
        self._events.execution_started()
        try:
            execution_result = self._runtime.execute(self._active_dataset, validated)
        except Exception as exc:
            # Attempt correction
            correction_result = self._correction_engine.correct(
                dataset=self._active_dataset,
                profile=self._active_profile,
                original_prompt_request=prompt_request,
                original_response=parsed.success,
                original_validated=validated,
                execution_error=exc,
            )
            self._events.execution_completed(correction_result.execution_result.execution_time_ms)
            return EngineResult(
                execution_result=correction_result.execution_result,
                corrected=correction_result.corrected,
                attempt_count=correction_result.attempt_count,
            )

        self._events.execution_completed(execution_result.execution_time_ms)
        return EngineResult(
            execution_result=execution_result,
            corrected=False,
            attempt_count=1,
        )

    def replace_dataset(self, file_path: str | Path) -> DatasetSummary:
        """Replace the active dataset with a new one.

        Equivalent to uploading a new dataset and discarding the old session.

        Args:
            file_path: Path to the new dataset file.

        Returns:
            DatasetSummary for the new dataset.
        """
        self.clear_session()
        return self.upload_dataset(file_path)

    def clear_session(self) -> None:
        """Clear the active dataset session."""
        self._active_dataset = None
        self._active_profile = None
        self._events.session_cleared()

    def has_active_dataset(self) -> bool:
        """Check if there is an active dataset session."""
        return self._active_dataset is not None

    def get_dataset_summary(self) -> DatasetSummary:
        """Get a summary of the active dataset.

        Returns:
            DatasetSummary with lightweight information.

        Raises:
            NoActiveDatasetError: If no dataset is active.
        """
        if self._active_dataset is None:
            raise NoActiveDatasetError("No active dataset.")

        return self._build_dataset_summary(self._active_dataset)

    def get_dataset_preview(self) -> dict:
        """Get top 5 rows of the active dataset for preview.

        Returns:
            dict with keys: columns, rows, total_rows.

        Raises:
            NoActiveDatasetError: If no dataset is active.
        """
        if self._active_dataset is None:
            raise NoActiveDatasetError("No active dataset.")

        df = self._active_dataset.dataframe
        preview = df.head(5)
        columns = list(preview.columns)

        import numpy as np

        def _sanitize(val: Any) -> str | int | float | bool | None:
            if val is None:
                return None
            if isinstance(val, (int, float, bool, str)):
                return val
            if isinstance(val, (np.integer,)):
                return int(val)
            if isinstance(val, (np.floating,)):
                return float(val)
            if isinstance(val, (np.bool_,)):
                return bool(val)
            return str(val)

        rows = [[_sanitize(val) for val in row] for row in preview.itertuples(index=False)]
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(df),
        }

    def _build_dataset_summary(self, loaded: LoadedDataset) -> DatasetSummary:
        """Build a DatasetSummary from a LoadedDataset."""

        profile = self._active_profile
        return DatasetSummary(
            dataset_id=str(loaded.dataset_id),
            filename=loaded.filename,
            rows=loaded.row_count,
            columns=loaded.column_count,
            metadata={
                "file_size_bytes": loaded.file_size_bytes,
                "memory_usage_bytes": profile.memory_usage_bytes if profile else 0,
                "profile_duration_ms": profile.profile_duration_ms if profile else 0,
            },
        )
