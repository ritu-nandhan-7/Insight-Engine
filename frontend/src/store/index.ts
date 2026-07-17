/** Lightweight UI state management.
 *
 * Holds only UI concerns.
 * Backend state (figures, summaries) is managed by React Query.
 */

import { create, useStore } from "./vanilla";

interface UIState {
  /** Whether a dataset is currently active in the session. */
  isDatasetActive: boolean;
  setDatasetActive: (active: boolean) => void;

  /** Whether a query is currently being processed. */
  isQuerying: boolean;
  setQuerying: (querying: boolean) => void;
}

const storeApi = create<UIState>((set) => ({
  isDatasetActive: false,
  setDatasetActive: (active: boolean) => set({ isDatasetActive: active }),

  isQuerying: false,
  setQuerying: (querying: boolean) => set({ isQuerying: querying }),
}));

export { storeApi };

export function useUIState(): UIState {
  return useStore(storeApi);
}