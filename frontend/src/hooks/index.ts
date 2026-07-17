/** Custom React Query hooks for backend data. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getDatasetPreview, getDatasetSummary, uploadDataset } from "../api/dataset";
import { submitQuery } from "../api/query";
import { storeApi, useUIState } from "../store";
import type { EngineResult } from "../types";

export const DATASET_KEY = ["dataset"] as const;
export const PREVIEW_KEY = ["datasetPreview"] as const;
export const QUERY_KEY = ["lastQuery"] as const;

/** React Query hook: fetch dataset summary from GET /dataset.
 *
 * Enabled only when the UI store says a dataset is active.
 */
export function useDatasetSummary() {
  const { isDatasetActive } = useUIState();
  return useQuery({
    queryKey: DATASET_KEY,
    queryFn: getDatasetSummary,
    enabled: isDatasetActive,
    staleTime: Infinity,
    retry: false,
  });
}

/** React Query hook: fetch top 5 rows preview from GET /dataset/preview. */
export function useDatasetPreview() {
  const { isDatasetActive } = useUIState();
  return useQuery({
    queryKey: PREVIEW_KEY,
    queryFn: getDatasetPreview,
    enabled: isDatasetActive,
    staleTime: Infinity,
    retry: false,
  });
}

/** Mutation hook: upload a file, then invalidate dataset query on success. */
export function useUploadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadDataset,
    onSuccess: () => {
      storeApi.setState({ isDatasetActive: true });
      queryClient.invalidateQueries({ queryKey: DATASET_KEY });
      queryClient.invalidateQueries({ queryKey: PREVIEW_KEY });
    },
  });
}

/** Mutation hook: submit a query, cache the EngineResult on success. */
export function useQueryMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: submitQuery,
    onSuccess: (result: EngineResult) => {
      const prev = queryClient.getQueryData<EngineResult[]>(QUERY_KEY) ?? [];
      const next = [result, ...prev];
      queryClient.setQueryData(QUERY_KEY, next);
    },
  });
}
