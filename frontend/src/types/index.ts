/** Frontend type models matching the backend API responses. */

export interface HealthResponse {
  status: "ok";
}

export interface QueryRequest {
  query: string;
}

export interface DatasetSummary {
  filename: string;
  rows: number;
  columns: number;
  file_size_bytes: number;
  memory_usage_bytes: number;
  profile_duration_ms: number;
}

export interface DataPreview {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  total_rows: number;
}

export interface EngineResult {
  status: "success";
  title: string;
  execution_time_ms: number;
  figure: Record<string, unknown>;
  query: string;
  timestamp: number;
}

export interface ApiError {
  status: "error";
  detail: string;
}
