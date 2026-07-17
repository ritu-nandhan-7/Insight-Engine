/** API functions for dataset endpoints. */

import { apiClient } from "./client";
import type { DataPreview, DatasetSummary } from "../types";

export async function uploadDataset(file: File): Promise<DatasetSummary> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<DatasetSummary>("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getDatasetSummary(): Promise<DatasetSummary> {
  const { data } = await apiClient.get<DatasetSummary>("/dataset");
  return data;
}

export async function getDatasetPreview(): Promise<DataPreview> {
  const { data } = await apiClient.get<DataPreview>("/dataset/preview");
  return data;
}

export async function clearDataset(): Promise<void> {
  await apiClient.delete("/dataset");
}
