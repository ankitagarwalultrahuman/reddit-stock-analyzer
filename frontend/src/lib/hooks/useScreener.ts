"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

/**
 * Hook for long-running async tasks with polling.
 * Returns { start, status, result, error, isRunning }
 */
export function useAsyncTask<TResult = unknown>(
  startFn: () => Promise<{ task_id: string }>,
  pollFn: (taskId: string) => Promise<TaskResult<TResult>>,
  pollInterval = 2000
) {
  const [taskId, setTaskId] = useState<string | null>(null);

  const start = useCallback(async () => {
    const { task_id } = await startFn();
    setTaskId(task_id);
  }, [startFn]);

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

  return {
    start,
    reset,
    taskId,
    status: data?.status ?? (taskId ? "running" : "idle"),
    result: data?.result ?? null,
    error: data?.error ?? null,
    isRunning: !!taskId && data?.status === "running",
    isComplete: data?.status === "complete",
    isError: data?.status === "error",
  };
}

export function useScreenerScan() {
  const [params, setParams] = useState({ watchlist: "NIFTY50", strategy: "oversold_reversal", min_matches: 2 });

  const task = useAsyncTask(
    () => api.startScan(params.watchlist, params.strategy, params.min_matches),
    api.getScanResult
  );

  return { ...task, params, setParams };
}

export function useSwingScan() {
  const [params, setParams] = useState({ watchlist: "NIFTY50", min_score: 60 });

  const task = useAsyncTask(
    () => api.startSwingScan(params.watchlist, params.min_score),
    api.getSwingResult
  );

  return { ...task, params, setParams };
}

export function useSectorAnalysis() {
  return useAsyncTask(api.startSectorAnalysis, api.getSectorResult, 3000);
}

export function useWeeklyPulse() {
  const [watchlist, setWatchlist] = useState("NIFTY50");

  const task = useAsyncTask(
    () => api.startWeeklyPulse(watchlist),
    api.getWeeklyResult,
    3000
  );

  return { ...task, watchlist, setWatchlist };
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: api.getStrategies,
    staleTime: Infinity,
  });
}
