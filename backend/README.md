# Backend

This folder contains the FastAPI application and all backend-only concerns.

## Planned Responsibility Layers

- `app/api`: HTTP route handlers and request/response boundaries
- `app/core`: configuration, constants, security policies, and application wiring
- `app/data`: dataset loading and DataFrame preparation
- `app/llm`: Gemini integration and prompt assembly
- `app/execution`: safe execution of generated Python code
- `app/visualization`: Plotly figure handling and formatting
- `app/sessions`: session lifecycle and request context tracking
- `app/schemas`: Pydantic request and response models
- `app/utils`: shared helpers with no domain ownership
- `tests`: backend tests and backend-focused validation

## Current State

Only the folder structure and documentation are present. No runtime logic has been implemented yet.
