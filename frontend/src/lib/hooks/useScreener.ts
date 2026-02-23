"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

/**
 * Hook for long-running async tasks with polling.
 * Persists taskId in sessionStorage so results survive tab navigation.
 */
export function useAsyncTask<TResult = unknown>(
  startFn: () => Promise<{ task_id: string }>,
  pollFn: (taskId: string) => Promise<TaskResult<TResult>>,
  pollInterval = 2000,
  storageKey?: string
) {
  const [taskId, setTaskId] = useState<string | null>(() => {
    if (storageKey && typeof window !== "undefined") {
      return sessionStorage.getItem(storageKey);
    }
    return null;
  });
  const startFnRef = useRef(startFn);
  startFnRef.current = startFn;

  // Keep sessionStorage in sync with taskId
  useEffect(() => {
    if (!storageKey) return;
    if (taskId) {
      sessionStorage.setItem(storageKey, taskId);
    } else {
      sessionStorage.removeItem(storageKey);
    }
  }, [taskId, storageKey]);

  const start = useCallback(async () => {
    const { task_id } = await startFnRef.current();
    setTaskId(task_id);
  }, []);

  const { data } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => pollFn(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (d && d.status !== "running") return false;
      return pollInterval;
    },
  });

  const reset = useCallback(() => setTaskId(null), []);

  const restart = useCallback(async () => {
    setTaskId(null);
    const { task_id } = await startFnRef.current();
    setTaskId(task_id);
  }, []);

  return {
    start,
    reset,
    restart,
    taskId,
    status: data?.status ?? (taskId ? "running" : "idle"),
    result: data?.result ?? null,
    error: data?.error ?? null,
    isRunning: !!taskId && data?.status === "running",
    isComplete: data?.status === "complete",
    isError: data?.status === "error",
  };
}

/** Read persisted params from sessionStorage, falling back to defaults. */
function restoreParams<T>(key: string, defaults: T): T {
  if (typeof window === "undefined") return defaults;
  const stored = sessionStorage.getItem(key);
  if (!stored) return defaults;
  try {
    return { ...defaults, ...JSON.parse(stored) };
  } catch {
    return defaults;
  }
}

export function useScreenerScan() {
  const storageKey = "task:screener";
  const defaultParams = { watchlist: "NIFTY50", strategy: "oversold_reversal", min_matches: 2 };
  const [params, setParams] = useState(() => restoreParams(storageKey + ":params", defaultParams));
  const paramsRef = useRef(params);

  const paramKey = `${params.watchlist}:${params.strategy}:${params.min_matches}`;

  const updateParams = useCallback((newParams: typeof defaultParams) => {
    paramsRef.current = newParams;
    setParams(newParams);
    sessionStorage.setItem(storageKey + ":params", JSON.stringify(newParams));
  }, []);

  const task = useAsyncTask(
    () => api.startScan(paramsRef.current.watchlist, paramsRef.current.strategy, paramsRef.current.min_matches),
    api.getScanResult,
    2000,
    storageKey + ":" + paramKey
  );

  return { ...task, params, setParams: updateParams };
}

export function useSwingScan() {
  const storageKey = "task:swing";
  const defaultParams = { watchlist: "NIFTY50", min_score: 60 };
  const [params, setParams] = useState(() => restoreParams(storageKey + ":params", defaultParams));
  const paramsRef = useRef(params);

  const paramKey = `${params.watchlist}:${params.min_score}`;

  const updateParams = useCallback((newParams: typeof defaultParams) => {
    paramsRef.current = newParams;
    setParams(newParams);
    sessionStorage.setItem(storageKey + ":params", JSON.stringify(newParams));
  }, []);

  const task = useAsyncTask(
    () => api.startSwingScan(paramsRef.current.watchlist, paramsRef.current.min_score),
    api.getSwingResult,
    2000,
    storageKey + ":" + paramKey
  );

  return { ...task, params, setParams: updateParams };
}

export function useSectorAnalysis() {
  return useAsyncTask(api.startSectorAnalysis, api.getSectorResult, 3000, "task:sectors");
}

export function useETFAnalysis() {
  return useAsyncTask(api.startETFAnalysis, api.getETFResult, 3000, "task:etf");
}

export function useWeeklyPulse() {
  const storageKey = "task:weekly";
  const [watchlist, setWatchlist] = useState(() => {
    if (typeof window === "undefined") return "NIFTY50";
    return sessionStorage.getItem(storageKey + ":params") ?? "NIFTY50";
  });
  const watchlistRef = useRef(watchlist);

  const updateWatchlist = useCallback((w: string) => {
    watchlistRef.current = w;
    setWatchlist(w);
    sessionStorage.setItem(storageKey + ":params", w);
  }, []);

  const task = useAsyncTask(
    () => api.startWeeklyPulse(watchlistRef.current),
    api.getWeeklyResult,
    3000,
    storageKey + ":" + watchlist
  );

  return { ...task, watchlist, setWatchlist: updateWatchlist };
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: api.getStrategies,
    staleTime: Infinity,
  });
}
