"""Python runtime for executing validated AI-generated code."""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.dataset import LoadedDataset

from .constants import EXECUTION_NAMESPACE_KEYS, REQUIRED_OUTPUT_VARIABLE
from .exceptions import FigureNotFoundError, RuntimeExecutionError
from .models import ExecutionResult

logger = logging.getLogger(__name__)


class _RuntimeLogger:
    """Keeps runtime logging separate from execution logic."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def execution_started(self) -> None:
        self._logger.info("Execution started")

    def environment_prepared(self) -> None:
        self._logger.info("Execution environment prepared")

    def python_executed(self) -> None:
        self._logger.info("Python executed")

    def figure_generated(self) -> None:
        self._logger.info("Figure generated")

    def execution_completed(self, execution_time_ms: float) -> None:
        self._logger.info("Execution completed (time=%.2fms)", execution_time_ms)


class PythonRuntime:
    """Execute validated Python code in a controlled environment.

    The runtime:
    - Receives a LoadedDataset and ValidatedCode
    - Prepares a restricted execution namespace
    - Executes the code using exec()
    - Returns the generated Plotly figure
    """

    def __init__(self) -> None:
        self._events = _RuntimeLogger(logger)

    def execute(self, dataset: LoadedDataset, validated_code: "ValidatedCode") -> ExecutionResult:
        """Execute validated Python code and return the generated figure.

        Args:
            dataset: The loaded dataset containing the DataFrame.
            validated_code: The validated Python code to execute.

        Returns:
            ExecutionResult containing the figure and execution time.

        Raises:
            RuntimeExecutionError: If code execution fails.
            FigureNotFoundError: If the code does not assign to `fig`.
        """
        self._events.execution_started()

        # Prepare execution namespace
        namespace = self._prepare_namespace(dataset)
        self._events.environment_prepared()

        # Execute the code
        start_time = time.perf_counter()
        try:
            exec(validated_code.python_code, namespace)  # noqa: S102
            self._events.python_executed()
        except Exception as exc:
            raise RuntimeExecutionError(f"Code execution failed: {exc}") from exc

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Verify figure was created
        if REQUIRED_OUTPUT_VARIABLE not in namespace:
            raise FigureNotFoundError(
                f"Code executed successfully but did not assign a figure to '{REQUIRED_OUTPUT_VARIABLE}'"
            )

        figure = namespace[REQUIRED_OUTPUT_VARIABLE]
        self._events.figure_generated()
        self._events.execution_completed(execution_time_ms)

        return ExecutionResult(
            figure=figure,
            execution_time_ms=execution_time_ms,
        )

    def _prepare_namespace(self, dataset: LoadedDataset) -> dict[str, Any]:
        """Prepare the execution namespace with allowed variables only."""

        import pandas as pd
        import numpy as np
        import plotly.express as px
        import plotly.graph_objects as go

        return {
            "df": dataset.dataframe,
            "pd": pd,
            "np": np,
            "px": px,
            "go": go,
        }