# Insight Engine — Complete Architecture

> **Audience:** Project developers (not end users).
> **Scope:** The entire project — backend, FastAPI layer, and React frontend.
> **Principle:** Every module has ONE responsibility. The backend owns all business logic. Gemini ONLY generates Python analysis code. Raw datasets NEVER leave the backend.

This document explains every architectural decision, based strictly on the existing code. It does not propose changes.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Dataset Loader](#2-dataset-loader)
3. [Data Profiler](#3-data-profiler)
4. [Prompt Builder](#4-prompt-builder)
5. [Gemini Client](#5-gemini-client)
6. [Response Parser](#6-response-parser)
7. [Code Validator](#7-code-validator)
8. [Python Runtime](#8-python-runtime)
9. [Correction Engine](#9-correction-engine)
10. [InsightEngine (Facade)](#10-insightengine-facade)
11. [FastAPI Layer](#11-fastapi-layer)
12. [React Frontend](#12-react-frontend)
13. [Complete System Flow](#13-complete-system-flow)

---

## 1. Project Overview

### 1.1 Purpose
Insight Engine is an AI-powered data analysis platform that allows users to upload datasets and ask natural language questions. The backend profiles the data, builds a prompt for Gemini, generates Python analysis code, validates it, executes it locally, and returns a Plotly visualization. Raw datasets never leave the backend.

### 1.2 Technology Stack
**Backend:**
- Python 3.11+
- FastAPI (HTTP API)
- Pandas (data manipulation)
- Plotly (visualization)
- Google Gemini API (AI code generation)
- Pydantic (validation)

**Frontend:**
- React 18+ with TypeScript
- Vite (build tool)
- React Query (TanStack Query) — server state management
- Zustand-like vanilla store — UI state
- React-Plotly.js — chart rendering
- Axios — HTTP client

### 1.3 Architecture Principles
- **Single Responsibility:** Every module has ONE job.
- **Backend Ownership:** All business logic lives in the backend.
- **Privacy by Design:** Raw data never leaves the backend; only aggregates and figures are sent to the frontend.
- **Facade Pattern:** External consumers interact only with `InsightEngine`, never with internal modules.
- **Consistent Envelope:** All API responses use `{status: "success"|"error", ...}` format.

---

## 2. Dataset Loader

**Files:** `backend/dataset/loader.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 2.1 Purpose
Converts an uploaded file (path, file-like object, or upload object) into an in-memory `LoadedDataset` containing a pandas `DataFrame` plus file-level metadata. It is the single entry point for getting raw data into the engine.

### 2.2 Responsibilities
**Owns:**
- Detecting the file extension and selecting the correct pandas reader.
- Reading the bytes into a DataFrame with encoding fallback (UTF-8 → latin1 → ISO-8859-1 → cp1252 → utf-16).
- Computing file-level metadata (filename, extension, size, row/column counts).
- Validating that the result is non-empty.
- Raising typed errors for unsupported/empty/corrupt files.

**Does NOT own:**
- Profiling or semantic analysis (owned by `DataProfiler`).
- Building prompts (owned by `PromptBuilder`).
- Executing analysis code (owned by `PythonRuntime`).
- Any knowledge of Gemini, Plotly, or the AI pipeline.

### 2.3 Inputs
- `load(file: Any) -> LoadedDataset`
  - `file` may be: a filesystem path (`str`/`os.PathLike`), an object with `.file` + `.filename` (e.g. a FastAPI `UploadFile`), or any object with `.name`/`.size`/`.seek`/`.tell`.

### 2.4 Outputs
- `LoadedDataset` (frozen, slots):
  - `dataframe: pd.DataFrame`
  - `filename: str`
  - `extension: str`
  - `file_size_bytes: int`
  - `row_count: int`, `column_count: int`
  - `dataset_id: UUID` (auto-generated)
  - `loaded_at: datetime` (auto-generated)

### 2.5 Internal Flow
```
load(file)
  └─ _build_source(file)
       ├─ _resolve_filename  → filename
       ├─ _resolve_extension → extension
       ├─ _resolve_file_size → bytes
       └─ _resolve_target    → readable stream
  └─ _loaders.get(extension) → raises UnsupportedFileTypeError if unknown
  └─ _rewind_target(target)
  └─ loader(target) → pd.read_csv / read_excel / read_json / read_parquet
       └─ on UnicodeDecodeError → try latin1, ISO-8859-1, cp1252, utf-16
       └─ on parse error → CorruptedDatasetError
  └─ _validate_dataframe(df) → raises EmptyDatasetError if df.empty
  └─ _build_loaded_dataset → LoadedDataset(...)
```

### 2.6 Models
- `LoadedDataset` is **frozen + slots**. Immutability guarantees that once a dataset enters the pipeline, no module can silently mutate it.

### 2.7 Exceptions
- `DatasetError` — base.
- `UnsupportedFileTypeError` — extension missing or not supported.
- `DatasetLoadError` — cannot read the file.
- `EmptyDatasetError` — resulting DataFrame has zero rows.
- `CorruptedDatasetError` — file exists but cannot be parsed.

### 2.8 Design Decisions
- **Encoding fallback:** CSV files may use various encodings; the loader tries UTF-8 first, then falls back to common Windows/Latin encodings.
- **Single responsibility:** the loader knows nothing about analysis.

---

## 3. Data Profiler

**Files:** `backend/profiler/profiler.py`, `analyzers.py`, `semantic_detector.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 3.1 Purpose
Turns a `LoadedDataset` into a **privacy-safe `DatasetProfile`** — a structural, statistical description of the data that contains NO raw row values. This profile is what Gemini sees, so raw data never leaves the backend.

### 3.2 Responsibilities
**Owns:**
- Per-column semantic-type detection (Numeric, Categorical, Text, Boolean, Datetime, ID, Unknown).
- Per-column statistics (numeric quartiles, categorical top values, text lengths, datetime ranges, boolean counts).
- Dataset-level quality metrics (duplicates, missingness, constant/high-cardinality/potential-key columns).
- Objective warnings derived from those metrics.
- Memory usage and profiling duration.

### 3.3 Inputs
- `profile(loaded_dataset: LoadedDataset) -> DatasetProfile`

### 3.4 Outputs
- `DatasetProfile` (frozen, slots):
  - `dataset_id`, `filename`, `rows`, `columns`
  - `memory_usage_bytes`, `file_size_bytes`
  - `profiled_at`, `profile_duration_ms`
  - `column_profiles: tuple[ColumnProfile, ...]`
  - `quality_profile: DatasetQualityProfile`
  - `warnings: tuple[DatasetWarning, ...]`

### 3.5 Internal Flow
```
profile(loaded_dataset)
  └─ _validate_input
  └─ _analyze_columns(dataframe)
       └─ for each column:
            semantic_type = ColumnAnalyzer.detect_semantic_type(...)
            ColumnAnalyzer.analyze(...) → ColumnProfile
  └─ DatasetQualityAnalyzer.analyze(...) → DatasetQualityProfile
  └─ DatasetWarningAnalyzer.analyze(...) → tuple[DatasetWarning]
  └─ _build_profile(...) → DatasetProfile
```

### 3.6 Design Decisions
- **Privacy by construction:** the profile stores aggregates and top-value counts, never raw cell values.
- **Deterministic semantic detection:** avoids nondeterministic model calls; profiling is fast and offline.

---

## 4. Prompt Builder

**Files:** `backend/prompt_builder/builder.py`, `serializer.py`, `templates.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 4.1 Purpose
Converts a `DatasetProfile` + user query into a `PromptRequest` — the immutable, three-part instruction sent to Gemini.

### 4.2 Responsibilities
**Owns:**
- Validating that a profile and a non-empty query exist.
- Serializing the profile into a compact, token-efficient `SerializedDataset`.
- Assembling the `PromptRequest` (system prompt + dataset context + user query).

### 4.3 Inputs
- `build(profile: DatasetProfile, query: str) -> PromptRequest`

### 4.4 Outputs
- `PromptRequest` (frozen, slots):
  - `system_prompt: str` — the fixed template with rules + response contract.
  - `dataset_context: SerializedDataset` — compact column info.
  - `user_query: str` — the cleaned question.

### 4.5 Internal Flow
```
build(profile, query)
  └─ validate inputs
  └─ DatasetSerializer.serialize(profile) → SerializedDataset
  └─ PromptRequest(system_prompt=TEMPLATE, dataset_context=..., user_query=stripped)
```

### 4.6 Design Decisions
- **Contract in the template:** the rules ("no imports", "assign `fig`") live in one template so they are easy to audit and change.
- **Compact serialization:** drops everything Gemini doesn't need, reducing token cost.

---

## 5. Gemini Client

**Files:** `backend/gemini/client.py`, `config.py`, `models.py`, `exceptions.py`, `__init__.py`, `constants.py`

### 5.1 Purpose
A thin, pure communication layer to the Gemini API. It accepts a `PromptRequest`, calls Gemini, and returns the **raw, untouched** response.

### 5.2 Responsibilities
**Owns:**
- Building the Gemini SDK call (system instruction + contents).
- Retry/backoff for transient failures (429, 5xx, API errors).
- Mapping SDK errors to typed `Gemini*` exceptions.
- Wrapping the SDK response into `RawGeminiResponse`.

### 5.3 Inputs
- `generate(prompt_request: PromptRequest) -> RawGeminiResponse`

### 5.4 Outputs
- `RawGeminiResponse` (frozen, slots):
  - `raw_text: str` — the exact text Gemini returned.
  - `model_name`, `finish_reason`, `response_id`
  - `usage: UsageInfo | None`

### 5.5 Internal Flow
```
generate(prompt_request)
  └─ _build_system_instruction → prompt_request.system_prompt
  └─ _build_contents → "Dataset Context:\n{json}\n\nUser Question:\n{query}"
  └─ _call_with_retry(system_instruction, contents)
       └─ loop up to retry.max_attempts:
            ├─ models.generate_content(...)
            ├─ 429 → GeminiRateLimitError (retry w/ exponential backoff)
            ├─ 401/403 → GeminiAuthenticationError (no retry)
            └─ unexpected → GeminiConnectionError
  └─ _to_raw_response → RawGeminiResponse
```

### 5.6 Design Decisions
- **Transport only:** no domain logic. This makes the client swappable.
- **Exponential backoff on 429/5xx:** resilient to transient cloud failures.
- **Config from env:** reads `GEMINI_API_KEY`/`GEMINI_MODEL` from `.env`.

---

## 6. Response Parser

**Files:** `backend/parser/parser.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 6.1 Purpose
Turns the `RawGeminiResponse.raw_text` into a strongly typed `ParsedGeminiResponse`. It extracts JSON from free-form text that may include markdown fences or surrounding prose.

### 6.2 Responsibilities
**Owns:**
- Extracting the JSON object from raw text.
- Validating the `status` field and required fields per status.
- Building the typed `SuccessResponse` / `ClarificationResponse` / `ErrorResponse`.

### 6.3 Inputs
- `parse(raw_response: RawGeminiResponse) -> ParsedGeminiResponse`

### 6.4 Outputs
- `ParsedGeminiResponse` (frozen, slots):
  - `status: str` — one of `success`, `clarification`, `error`
  - Exactly one of: `success: SuccessResponse`, `clarification: ClarificationResponse`, `error: ErrorResponse`

### 6.5 Internal Flow
```
parse(raw_response)
  └─ _extract_json(raw_text)
       ├─ strip; try ```json ... ``` fence
       ├─ else find first '{' and match balanced braces
       └─ raise InvalidJsonError if none found
  └─ json.loads → must be a dict
  └─ validate status and required fields
  └─ build ParsedGeminiResponse
```

### 6.6 Design Decisions
- **Robust extraction:** real LLM output is messy; the brace-balancing extractor tolerates prose and markdown.
- **Strict contract validation:** rejecting unknown statuses / missing fields early prevents downstream garbage.

---

## 7. Code Validator

**Files:** `backend/validator/validator.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 7.1 Purpose
Statically checks AI-generated Python against the **execution contract** before it runs. This is the security boundary of the system.

### 7.2 Responsibilities
**Owns:**
- AST syntax check.
- Forbidding `import` / `import from` statements.
- Forbidding dangerous built-ins (`eval`, `exec`, `compile`, `open`, `input`, `__import__`).
- Forbidding references to dangerous modules (`os`, `subprocess`, `socket`, `requests`, `pathlib`, `shutil`, `sys`, `builtins`).
- Requiring assignment to the output variable `fig`.

### 7.3 Inputs
- `validate(python_code: str) -> ValidatedCode`

### 7.4 Outputs
- `ValidatedCode` (frozen, slots):
  - `python_code: str`
  - `is_valid: bool`
  - `errors: tuple[str, ...]`

### 7.5 Internal Flow
```
validate(python_code)
  └─ ast.parse → SyntaxError? → return is_valid=False
  └─ _check_imports(tree)
  └─ _check_functions(tree)
  └─ _check_module_references(tree)
  └─ _check_fig_assignment(tree)
  └─ is_valid = (no errors); return ValidatedCode
```

### 7.6 Design Decisions
- **Static-only (AST):** no execution during validation, so invalid code can never run.
- **Accumulate errors:** returning all violations at once is better UX.
- **Forbidden lists in constants:** security policy is data, easy to review/extend.

---

## 8. Python Runtime

**Files:** `backend/runtime/runtime.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 8.1 Purpose
Executes **validated** Python code against the active dataset and returns the resulting Plotly figure.

### 8.2 Responsibilities
**Owns:**
- Preparing a restricted execution namespace (`df`, `pd`, `np`, `px`, `go`).
- Running the code via `exec`.
- Timing execution.
- Extracting the `fig` variable and wrapping it in `ExecutionResult`.

### 8.3 Inputs
- `execute(dataset: LoadedDataset, validated_code: ValidatedCode) -> ExecutionResult`

### 8.4 Outputs
- `ExecutionResult` (frozen, slots):
  - `figure: Any` — the Plotly figure object.
  - `execution_time_ms: float`
  - `metadata: dict`

### 8.5 Internal Flow
```
execute(dataset, validated_code)
  └─ namespace = _prepare_namespace(dataset)
       └─ {"df": dataframe, "pd": pandas, "np": numpy, "px": plotly.express, "go": plotly.graph_objects}
  └─ start = perf_counter()
  └─ exec(validated_code.python_code, namespace)
  └─ execution_time_ms = (perf_counter() - start) * 1000
  └─ if "fig" not in namespace → FigureNotFoundError
  └─ figure = namespace["fig"]
  └─ return ExecutionResult(figure, execution_time_ms)
```

### 8.6 Design Decisions
- **Restricted namespace:** only the five promised names are injected.
- **`exec` is acceptable here** because code is pre-validated by the validator.

---

## 9. Correction Engine

**Files:** `backend/correction/engine.py`, `models.py`, `constants.py`, `exceptions.py`, `__init__.py`

### 9.1 Purpose
Automatically retries the pipeline when execution fails, by asking Gemini to fix the code using the original error.

### 9.2 Responsibilities
**Owns:**
- Building a correction prompt (original context + error message).
- Re-running the generate → parse → validate → execute loop up to `MAX_CORRECTION_ATTEMPTS` (3).
- Returning a `CorrectionResult` (or raising if all attempts fail).

### 9.3 Inputs
- `correct(dataset, profile, original_prompt_request, original_response, original_validated, execution_error) -> CorrectionResult`

### 9.4 Outputs
- `CorrectionResult` (frozen, slots):
  - `execution_result: ExecutionResult`
  - `attempt_count: int`
  - `corrected: bool`

### 9.5 Internal Flow
```
correct(...)
  └─ for attempt in 1..MAX_CORRECTION_ATTEMPTS:
       ├─ build correction_prompt (same context, query + error)
       ├─ gemini_client.generate(correction_prompt)
       ├─ parser.parse → must be status=="success"
       ├─ validator.validate → must be is_valid
       ├─ runtime.execute(dataset, validated)
       └─ on success → return CorrectionResult(result, attempt, corrected=(attempt>1))
            on failure → if last attempt → raise CorrectionAttemptsExceeded
```

### 9.6 Design Decisions
- **Reuse, don't reimplement:** composes the same modules the facade uses.
- **Bounded retries (3):** prevents infinite loops and runaway cost.

---

## 10. InsightEngine (Facade)

**Files:** `backend/engine/engine.py`, `models.py`, `exceptions.py`, `constants.py`, `__init__.py`

### 10.1 Purpose
The single public entry point for the entire AI Core pipeline. It owns one instance of every module, manages the active dataset session in memory, and orchestrates: load → profile → prompt → generate → parse → validate → execute → (correct).

### 10.2 Responsibilities
**Owns:**
- Instantiating and holding all module instances.
- The active dataset session (`_active_dataset`, `_active_profile`).
- Orchestrating the pipeline and returning `EngineResult` / `DatasetSummary`.

### 10.3 Public Methods
- `upload_dataset(file_path: str | Path) -> DatasetSummary`
- `ask(user_query: str) -> EngineResult`
- `replace_dataset(file_path) -> DatasetSummary`
- `clear_session() -> None`
- `has_active_dataset() -> bool`
- `get_dataset_summary() -> DatasetSummary`
- `get_dataset_preview() -> dict` — returns top 5 rows for preview

### 10.4 Internal Flow
```
upload_dataset(path):
  └─ loader.load(path) → LoadedDataset
  └─ profiler.profile(loaded) → DatasetProfile
  └─ store as _active_dataset / _active_profile
  └─ _build_dataset_summary(loaded) → DatasetSummary

ask(query):
  └─ prompt_builder.build(profile, query) → PromptRequest
  └─ gemini_client.generate(request) → RawGeminiResponse
  └─ parser.parse → ParsedGeminiResponse
  └─ validator.validate(parsed.success.python) → ValidatedCode
  └─ try: runtime.execute(dataset, validated) → ExecutionResult
  └─ except: correction_engine.correct(...) → CorrectionResult
  └─ return EngineResult(result, corrected, attempt_count)
```

### 10.5 Models
- `DatasetSummary` (frozen, slots): `dataset_id`, `filename`, `rows`, `columns`, `metadata`.
- `EngineResult` (frozen, slots): `execution_result`, `corrected`, `attempt_count`, `metadata`.

### 10.6 Design Decisions
- **One facade, one session:** a single in-memory dataset per engine instance.
- **Delegation over implementation:** the facade contains no analysis logic.
- **Correction is transparent:** `ask` returns the same `EngineResult` whether or not correction ran.

---

## 11. FastAPI Layer

**Files:** `backend/api/main.py`, `routes.py`, `schemas.py`, `dependencies.py`, `exceptions.py`, `__init__.py`

### 11.1 Purpose
The HTTP boundary. It exposes the engine to clients (React frontend, CLI, tests) and translates HTTP ↔ `InsightEngine`.

### 11.2 Responsibilities
**Owns:**
- Defining routes, request/response schemas, and HTTP status codes.
- Accepting file uploads, writing a temp file, and delegating to `engine.upload_dataset`.
- Mapping engine exceptions to consistent JSON error responses.
- Serializing the Plotly figure to JSON for the response.

### 11.3 Endpoints

#### `GET /health`
- **Purpose:** Health check.
- **Response:** `HealthResponse{ status: "ok" }`

#### `POST /upload`
- **Purpose:** Upload and profile a dataset, replacing any active session.
- **Request:** `multipart/form-data` with `file` field.
- **Response:** `DatasetSummaryResponse`
  - `filename: str` — original uploaded filename.
  - `rows: int`, `columns: int`
  - `file_size_bytes: int`, `memory_usage_bytes: int`
  - `profile_duration_ms: int`
- **Flow:**
  1. Receive `UploadFile`.
  2. Write to `tempfile.NamedTemporaryFile(delete=False, suffix=ext)`.
  3. Call `engine.upload_dataset(tmp_path)`.
  4. Delete temp file in `finally`.
  5. Return summary with original filename.

#### `POST /query`
- **Purpose:** Process a user query against the active dataset.
- **Request:** `QueryRequest{ query: str }`
- **Response:** `EngineResultResponse`
  - `status: "success"`
  - `title: str`
  - `execution_time_ms: float`
  - `figure: dict` — `json.loads(figure.to_json())`
  - `query: str` — the original query text
  - `timestamp: float` — Unix timestamp
- **Flow:**
  1. Call `engine.ask(request.query)`.
  2. Extract figure from `result.execution_result.figure`.
  3. Serialize with `json.loads(figure.to_json())`.
  4. Return response with query and timestamp.

#### `GET /dataset`
- **Purpose:** Get the active dataset summary.
- **Response:** `DatasetSummaryResponse`

#### `GET /dataset/preview`
- **Purpose:** Get the top 5 rows of the active dataset for preview.
- **Response:** `DataPreviewResponse`
  - `columns: list[str]`
  - `rows: list[list[str | int | float | bool | None]]`
  - `total_rows: int`

#### `DELETE /dataset`
- **Purpose:** Clear the active dataset session.
- **Response:** HTTP 204 No Content.

### 11.4 Error Handling
- `NoActiveDatasetError` → `NoActiveDatasetHTTPError` (400, `{"status":"error","detail":"..."}`).
- Any other engine error → `EngineHTTPError` (500, `{"status":"error","detail":"..."}`).

### 11.5 Design Decisions
- **Facade-only access:** routes import only `InsightEngine`/`NoActiveDatasetError`.
- **Singleton engine:** one `InsightEngine` per process preserves the single active session.
- **Temp file for upload:** FastAPI `UploadFile` is a stream; persisted to temp file, then deleted.
- **Consistent JSON envelope:** success and error responses both carry a `status` field.

---

## 12. React Frontend

**Location:** `frontend/`

### 12.1 Technology Stack
- **React 18+** with TypeScript
- **Vite** — build tool and dev server
- **TanStack Query (React Query)** — server state management, caching, and synchronization
- **Zustand-like vanilla store** — lightweight UI state (`isDatasetActive`)
- **React-Plotly.js** — Plotly chart rendering
- **Axios** — HTTP client for API calls

### 12.2 Project Structure
```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── public/
│   └── (static assets)
└── src/
    ├── main.tsx                    # App entry point
    ├── App.tsx                     # Root component
    ├── vite-env.d.ts              # Vite type declarations
    ├── api/
    │   ├── client.ts              # Axios instance with base URL
    │   ├── dataset.ts             # API functions: uploadDataset, getDatasetSummary, getDatasetPreview, clearDataset
    │   ├── query.ts               # API function: submitQuery
    │   └── index.ts               # Barrel exports
    ├── components/
    │   ├── layout/
    │   │   └── Layout.tsx         # Main layout wrapper
    │   ├── upload/
    │   │   └── Upload.tsx         # File upload component
    │   ├── dataset/
    │   │   └── DatasetSummary.tsx # Dataset info + data preview table
    │   ├── query/
    │   │   └── QueryBox.tsx       # Query input + submit button
    │   ├── chart/
    │   │   └── Chart.tsx          # Visualization display with multiple chart support
    │   └── (index.ts files)       # Barrel exports per component
    ├── hooks/
    │   └── index.ts               # React Query hooks: useDatasetSummary, useDatasetPreview, useUploadMutation, useQueryMutation
    ├── pages/
    │   └── HomePage.tsx           # Main page composing all components
    ├── store/
    │   ├── vanilla.ts             # Minimal Zustand-like store implementation
    │   └── index.ts               # UI state: isDatasetActive
    ├── styles/
    │   └── index.css              # Global styles
    └── types/
        └── index.ts               # TypeScript interfaces matching backend responses
```

### 12.3 State Management

**Server State (TanStack Query):**
- `useDatasetSummary()` — fetches `GET /dataset`, enabled only when dataset is active.
- `useDatasetPreview()` — fetches `GET /dataset/preview`, enabled only when dataset is active.
- `useUploadMutation()` — uploads file via `POST /upload`, invalidates dataset/preview caches on success.
- `useQueryMutation()` — submits query via `POST /query`, appends result to query history array.

**UI State (Vanilla Store):**
- `isDatasetActive: boolean` — tracks whether a dataset is currently loaded.
- Updated by `useUploadMutation` on success and by `clearDataset` on logout.

### 12.4 API Client

**Base Configuration (`client.ts`):**
- Axios instance with `baseURL: http://localhost:8000` (configurable via `.env`).
- Response interceptor for consistent error handling.

**API Functions:**
- `uploadDataset(file: File)` — `POST /upload` with `FormData`.
- `getDatasetSummary()` — `GET /dataset`.
- `getDatasetPreview()` — `GET /dataset/preview`.
- `clearDataset()` — `DELETE /dataset`.
- `submitQuery(query: string)` — `POST /query`.

### 12.5 Components

**Upload (`Upload.tsx`):**
- File input accepting `.csv,.xls,.xlsx,.json,.parquet`.
- Shows "Selected: filename" when file chosen, "Uploaded: filename" in green after success.
- Disabled during upload.
- Error display in red.

**DatasetSummary (`DatasetSummary.tsx`):**
- Shows: Rows, Columns, File Size, Memory Usage.
- Shows scrollable data preview table with top 5 rows (like Kaggle).
- Table has sticky headers, alternating row colors, horizontal scroll for many columns.
- Null values shown in italic gray.

**QueryBox (`QueryBox.tsx`):**
- Textarea for natural language questions.
- "Analyze" button with loading state ("Analyzing...").
- Error messages in red.
- No execution status display.

**Chart (`Chart.tsx`):**
- Subscribes to React Query cache for real-time updates.
- Displays all query results as a list (newest first).
- Each chart card shows: query text, timestamp, execution time.
- Plotly toolbar with camera icon for PNG export per chart.
- Shows chart count ("3 charts").
- No limit on number of stored visualizations.

**Layout (`Layout.tsx`):**
- Simple wrapper providing consistent page structure.

**HomePage (`HomePage.tsx`):**
- Composes: `Upload` → `DatasetSummary` → `QueryBox` → `Chart`.
- No Timeline/Execution Status component.

### 12.6 TypeScript Types

**Frontend types (`types/index.ts`):**
- `DatasetSummary` — matches backend `DatasetSummaryResponse`.
- `DataPreview` — matches backend `DataPreviewResponse`.
- `EngineResult` — matches backend `EngineResultResponse` plus `query` and `timestamp`.
- `ApiError` — matches backend error envelope.

### 12.7 Design Decisions
- **React Query for server state:** automatic caching, background refetching, and cache invalidation.
- **Vanilla store for UI state:** minimal dependency, only tracks `isDatasetActive`.
- **Barrel exports:** each folder has `index.ts` for clean imports.
- **No execution status:** removed per user feedback; only errors are shown.
- **Multiple visualizations:** all query results stored in array, displayed newest-first.
- **PNG export:** uses Plotly's built-in camera icon in mode bar.

---

## 13. Complete System Flow

### 13.1 Actors
- **React (browser):** sends multipart `POST /upload`, then `POST /query` with JSON, then renders the figure.
- **FastAPI (uvicorn worker):** HTTP boundary, owns the singleton `InsightEngine`.
- **InsightEngine:** orchestrates the pipeline.
- **Internal modules:** loader, profiler, prompt_builder, gemini, parser, validator, runtime, correction.

### 13.2 Diagram — High Level
```
React ──POST /upload──▶ FastAPI ──▶ InsightEngine.upload_dataset
                                      ├─ DatasetLoader.load        → LoadedDataset
                                      └─ DataProfiler.profile      → DatasetProfile
                                         (stored as active session)
React ──POST /query──▶ FastAPI ──▶ InsightEngine.ask
                                      ├─ PromptBuilder.build       → PromptRequest
                                      ├─ GeminiClient.generate      → RawGeminiResponse
                                      ├─ ResponseParser.parse       → ParsedGeminiResponse
                                      ├─ CodeValidator.validate     → ValidatedCode
                                      ├─ PythonRuntime.execute      → ExecutionResult(fig)
                                      └─ (on failure) CorrectionEngine.correct → ExecutionResult
                                    FastAPI serializes fig.to_json() → React
```

### 13.3 Step-by-Step: Upload

1. **React** collects a file and `POST`s it as `multipart/form-data` to `/upload` with field name `file`.
2. **FastAPI** `upload_dataset` route receives `UploadFile = File(...)`. `get_engine()` returns the singleton `InsightEngine`.
3. The route writes the upload stream to a `tempfile.NamedTemporaryFile(delete=False, suffix=ext)` and records `tmp_path`.
4. `engine.upload_dataset(tmp_path)` is called:
   a. `path = Path(tmp_path).expanduser().resolve()`; if it doesn't exist → `EngineError`.
   b. `self._loader.load(path)` → `DatasetLoader.load`:
      - `_build_source` resolves filename/extension/size/target.
      - extension looked up in `_loaders` (csv/xls/xlsx/json/parquet); unknown → `UnsupportedFileTypeError`.
      - the matching pandas reader parses bytes → `DataFrame` (with encoding fallback for CSV).
      - empty DataFrame → `EmptyDatasetError`; parse failure → `CorruptedDatasetError`.
      - `_build_loaded_dataset` → `LoadedDataset(dataframe, filename, extension, file_size_bytes, row_count, column_count)` with auto `dataset_id` (UUID) and `loaded_at`.
   c. `self._profiler.profile(loaded)` → `DataProfiler.profile`:
      - validates input is a `LoadedDataset`.
      - `ColumnAnalyzer` + `SemanticDetector` build a `ColumnProfile` per column (semantic type, role, stats).
      - `DatasetQualityAnalyzer` builds `DatasetQualityProfile`.
      - `DatasetWarningAnalyzer` builds `tuple[DatasetWarning]`.
      - `_build_profile` assembles `DatasetProfile` (rows, columns, memory, duration, column_profiles, quality, warnings). **No raw rows are stored.**
   d. Engine stores `self._active_dataset = loaded` and `self._active_profile = profile` (the in-memory session).
   e. `_build_dataset_summary(loaded)` → `DatasetSummary(dataset_id, filename, rows, columns, metadata={})`.
5. Back in the route, `os.unlink(tmp_path)` deletes the temp file (in `finally`).
6. Route returns `DatasetSummaryResponse(filename, rows, columns, file_size_bytes, memory_usage_bytes, profile_duration_ms)` as JSON with HTTP 200.
7. **React** stores the summary and shows:
   - Dataset info: Rows, Columns, File Size, Memory Usage.
   - Data preview table: first 5 rows with column headers (horizontally scrollable).

### 13.4 Step-by-Step: Query

8. **React** `POST`s `{"query": "Show the top 10 products by total sales as a bar chart."}` to `/query`.
9. FastAPI `query` route parses the body into `QueryRequest` and calls `engine.ask(request.query)`.
10. `InsightEngine.ask`:
    a. If `_active_dataset`/`_active_profile` is `None` → raise `NoActiveDatasetError` (route converts to 400 JSON).
    b. `self._prompt_builder.build(profile, query)`:
       - validates profile not None, query not blank.
       - `DatasetSerializer.serialize(profile)` → `SerializedDataset` (compact columns: name/dtype/semantic_type + optional min/max/mean/earliest/latest/top_values, capped at 3).
       - assembles `PromptRequest(system_prompt=SYSTEM_PROMPT_TEMPLATE, dataset_context=serialized, user_query=stripped)`.
       - `SYSTEM_PROMPT_TEMPLATE` tells Gemini: `df/pd/np/px/go` exist, no imports, no file/network/OS, assign `fig`, return strict JSON.
    c. `self._gemini_client.generate(prompt_request)`:
       - builds `system_instruction` from `system_prompt`.
       - builds `contents` = `"Dataset Context:\n{json of column_info}\n\nUser Question:\n{query}"`.
       - `_call_with_retry` calls the Gemini SDK with `GenerateContentConfig(temperature, max_output_tokens, top_p, top_k)`.
       - on 429/5xx retries with exponential backoff; on 401/403 → auth error; other 4xx → response error.
       - `_to_raw_response` → `RawGeminiResponse(raw_text, model_name, finish_reason, usage)`.
    d. `self._parser.parse(raw_response)`:
       - `_extract_json` pulls the JSON object out of raw text (handles markdown fences / prose).
       - `json.loads`; checks `status ∈ {success, clarification, error}`; checks required fields.
       - builds `ParsedGeminiResponse` with `SuccessResponse(title, python)` (or clarification/error).
       - if `status != "success"` → engine raises `EngineError`.
    e. `self._validator.validate(parsed.success.python)`:
       - `ast.parse` (syntax); if invalid → `ValidatedCode(is_valid=False)`.
       - checks no imports, no forbidden functions (`eval/exec/compile/open/input/__import__`), no forbidden module references (`os/subprocess/socket/requests/pathlib/shutil/sys/builtins`), and assignment to `fig`.
       - returns `ValidatedCode(python_code, is_valid, errors)`. If `not is_valid` → engine raises `EngineError`.
    f. `self._runtime.execute(self._active_dataset, validated)`:
       - `_prepare_namespace` → `{"df": dataframe, "pd": pandas, "np": numpy, "px": plotly.express, "go": plotly.graph_objects}`.
       - `exec(code, namespace)`; times with `perf_counter`.
       - if `exec` raises → `RuntimeExecutionError`; if no `fig` in namespace → `FigureNotFoundError`.
       - extracts `fig = namespace["fig"]`; returns `ExecutionResult(figure=fig, execution_time_ms)`.
    g. **On execution exception**: engine calls `self._correction_engine.correct(dataset, profile, original_prompt_request, original_response, original_validated, execution_error)`:
       - builds a correction `PromptRequest` (same context, query + `[CORRECTION REQUEST]\n{error_message}`).
       - loops up to `MAX_CORRECTION_ATTEMPTS=3`: generate → parse → validate → execute.
       - on success returns `CorrectionResult(execution_result, attempt_count, corrected=(attempt>1))`.
       - if all fail → `CorrectionAttemptsExceeded` (engine lets it propagate → 500 JSON).
       - engine returns `EngineResult(correction_result.execution_result, corrected, attempt_count)`.
    h. On direct success, engine returns `EngineResult(execution_result, corrected=False, attempt_count=1)`.
11. Back in the route:
    - `figure = result.execution_result.figure`.
    - `title = figure.layout.title.text if ... else "Chart"`.
    - `EngineResultResponse(status="success", title=title, execution_time_ms=..., figure=json.loads(figure.to_json()), query=request.query, timestamp=...)`.
12. FastAPI serializes the response as JSON (HTTP 200):
    ```json
    {
      "status": "success",
      "title": "...",
      "execution_time_ms": 1218.17,
      "figure": { "data": [...], "layout": {...} },
      "query": "Show the top 10 products...",
      "timestamp": 1710000000.123
    }
    ```
13. **React** receives the JSON:
    - Appends result to query history array in React Query cache.
    - Reads `figure.data`/`figure.layout` and renders with Plotly.js.
    - Shows query text, timestamp, and execution time above each chart.
    - The raw dataset never left the backend — only the figure JSON and a summary did.

### 13.5 Error Paths

**No dataset:**
- If React calls `/query` before uploading, `engine.ask` raises `NoActiveDatasetError`.
- Route catches it and raises `NoActiveDatasetHTTPError` → HTTP 400 with `{"status":"error","detail":"No active dataset. Upload a dataset first."}`.
- React shows error in red.

**Engine failure:**
- If Gemini is down, returns non-success, or code is invalid, the engine raises `EngineError` (or correction raises `CorrectionAttemptsExceeded`).
- Route catches the generic `Exception` and raises `EngineHTTPError` → HTTP 500 with `{"status":"error","detail":"<message>"}`.

### 13.6 Session Lifecycle
```
POST /upload ──▶ active session set (dataset + profile)
POST /query  ──▶ uses active session; appends to query history
GET  /dataset ─▶ returns summary of active session
GET  /dataset/preview ─▶ returns top 5 rows
DELETE /dataset ▶ engine.clear_session() → active session = None
POST /upload again ▶ replaces active session
```

### 13.7 Key Invariants
1. **Privacy:** only `DatasetProfile` (aggregates) and the final `figure` JSON leave the backend. Raw `df` is never serialized or sent to Gemini.
2. **Contract:** generated code must use only `df/pd/np/px/go` and assign `fig`. Enforced by the system prompt + validator.
3. **Facade-only:** the API imports only `InsightEngine`/`NoActiveDatasetError`; all logic lives behind the facade.
4. **Single session:** one in-memory dataset per engine instance; the API keeps one engine for the process lifetime.
5. **Consistent envelope:** every success has `status:"success"`; every error has `status:"error"`.
6. **Frontend never touches raw data:** the React app only receives summaries, previews, and figure JSON.

### 13.8 Object Transformation Map
```
UploadFile (stream)
  → temp file path
  → LoadedDataset (DataFrame + metadata)        [DatasetLoader]
  → DatasetProfile (aggregates, no rows)         [DataProfiler]
  → (stored as active session)

user_query (str) + DatasetProfile
  → SerializedDataset (compact)                  [DatasetSerializer]
  → PromptRequest (system/context/query)         [PromptBuilder]

PromptRequest
  → RawGeminiResponse (raw text)                 [GeminiClient]
  → ParsedGeminiResponse (SuccessResponse)       [ResponseParser]
  → ValidatedCode (is_valid)                     [CodeValidator]
  → ExecutionResult (figure object)              [PythonRuntime]
     ↺ CorrectionResult on failure               [CorrectionEngine]

ExecutionResult.figure
  → figure.to_json() → dict                      [FastAPI route]
  → JSON response → React (Plotly.js)            [FastAPI / network]

React State:
  → DatasetSummary (rows, columns, sizes)
  → DataPreview (top 5 rows table)
  → EngineResult[] (query history with figures)
```

### 13.9 How to Debug a Failure
- **Upload fails:** look for `Dataset upload received` → `Loading <EXT> dataset` → either `Unsupported dataset format` (wrong extension), `Dataset loading failed` (corrupt), or `Dataset loaded successfully` + `Rows/Columns`.
- **Query returns 500:** look for `Query received` → `Prompt building started` → `Sending request to Gemini` → `Gemini request completed` → `Response parsing started` → `Code validation started` → `Execution started` → either `Execution completed` or `Correction started`. The last successful log before the error pinpoints the failing stage.
- **Figure missing:** `Figure generated` should appear; if not, the validator's `Figure assignment validation passed` will be absent → code didn't assign `fig`.
- **Rate limited:** `Retrying Gemini request (attempt x/5, delay=...)` appears; if it exhausts, `GeminiRateLimitError`.

### 13.10 Startup Commands
**Backend (Terminal 1):**
```bash
cd c:\Users\psytr\Desktop\Projects\insight_engine
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

**Frontend (Terminal 2):**
```bash
cd c:\Users\psytr\Desktop\Projects\insight_engine\frontend
npm run dev
```

**Access:** Open http://localhost:5173/ in browser.

---

*End of architecture document. This describes the system as built; no code was changed to produce it.*