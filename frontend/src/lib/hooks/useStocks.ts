"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export function useStockHistory(ticker: string | null, days = 30) {
  return useQuery({
    queryKey: ["stockHistory", ticker, days],
    queryFn: () => api.getStockHistory(ticker!, days),
    enabled: !!ticker,
  });
}

export function useStockTechnicals(ticker: string | null, days = 60) {
  return useQuery({
    queryKey: ["stockTechnicals", ticker, days],
    queryFn: () => api.getStockTechnicals(ticker!, days),
    enabled: !!ticker,
  });
}
