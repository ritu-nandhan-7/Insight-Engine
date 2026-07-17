/**
 * Minimal vanilla React state store (no external dependencies).
 *
 * API-compatible subset of Zustand's `create<T>()`.
 */

import { useSyncExternalStore } from "react";

type Setter<T> = (partial: Partial<T> | ((prev: T) => Partial<T>)) => void;

export interface StoreApi<T> {
  getState: () => T;
  setState: Setter<T>;
  subscribe: (listener: () => void) => () => void;
}

export function create<T>(createState: (set: Setter<T>, get: () => T) => T): StoreApi<T> {
  let state: T;
  const listeners = new Set<() => void>();

  const getState = (): T => state;

  const setState: Setter<T> = (partial) => {
    const next = typeof partial === "function" ? (partial as (prev: T) => Partial<T>)(state) : partial;
    state = { ...state, ...next };
    listeners.forEach((ls) => ls());
  };

  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  const api: StoreApi<T> = { getState, setState, subscribe };
  state = createState(api.setState, api.getState);

  return api;
}

export function useStore<T>(api: StoreApi<T>): T {
  return useSyncExternalStore(api.subscribe, api.getState);
}