"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export function useReportDates() {
  return useQuery({
    queryKey: ["reportDates"],
    queryFn: api.getReportDates,
  });
}

export function useReport(date: string | null) {
  return useQuery({
    queryKey: ["report", date],
    queryFn: () => api.getReport(date!),
    enabled: !!date,
  });
}

export function useSessions(date: string | null) {
  return useQuery({
    queryKey: ["sessions", date],
    queryFn: () => api.getSessions(date!),
    enabled: !!date,
  });
}

export function useActions(date: string | null) {
  return useQuery({
    queryKey: ["actions", date],
    queryFn: () => api.getActions(date!),
    enabled: !!date,
  });
}

export function useStockMentions(date: string | null) {
  return useQuery({
    queryKey: ["stocks", date],
    queryFn: () => api.getStocks(date!),
    enabled: !!date,
  });
}

export function useInsights(date: string | null) {
  return useQuery({
    queryKey: ["insights", date],
    queryFn: () => api.getInsights(date!),
    enabled: !!date,
  });
}

export function useSections(date: string | null) {
  return useQuery({
    queryKey: ["sections", date],
    queryFn: () => api.getSections(date!),
    enabled: !!date,
  });
}

export function useSentiment(date: string | null) {
  return useQuery({
    queryKey: ["sentiment", date],
    queryFn: () => api.getSentiment(date!),
    enabled: !!date,
  });
}

export function useComparison(date: string | null) {
  return useQuery({
    queryKey: ["comparison", date],
    queryFn: () => api.getComparison(date!),
    enabled: !!date,
    retry: false,
  });
}

export function useWeeklySummary() {
  return useQuery({
    queryKey: ["weeklySummary"],
    queryFn: api.getWeeklySummary,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useNewsHighlights() {
  return useQuery({
    queryKey: ["newsHighlights"],
    queryFn: api.getNewsHighlights,
    staleTime: 5 * 60 * 1000,
  });
}

export function useConfluenceSignals(date?: string) {
  return useQuery({
    queryKey: ["confluence", date],
    queryFn: () => api.getConfluenceSignals(date),
  });
}
