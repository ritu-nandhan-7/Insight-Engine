/** API functions for the query endpoint. */

import { apiClient } from "./client";
import type { EngineResult, QueryRequest } from "../types";

export async function submitQuery(query: string): Promise<EngineResult> {
  const payload: QueryRequest = { query };
  const { data } = await apiClient.post<EngineResult>("/query", payload);
  return data;
}