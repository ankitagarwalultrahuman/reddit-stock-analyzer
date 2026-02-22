"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";

export function useHoldings() {
  return useQuery({
    queryKey: ["holdings"],
    queryFn: api.getHoldings,
  });
}

export function useAddHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { ticker: string; quantity: number; avg_price: number }) =>
      api.addHolding(data.ticker, data.quantity, data.avg_price),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export function useRemoveHolding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticker: string) => api.removeHolding(ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holdings"] }),
  });
}

export function usePortfolioAnalysis() {
  return useQuery({
    queryKey: ["portfolioAnalysis"],
    queryFn: api.getPortfolioAnalysis,
    staleTime: 5 * 60 * 1000,
  });
}

export function useGrowwHoldings() {
  return useQuery({
    queryKey: ["growwHoldings"],
    queryFn: api.getGrowwHoldings,
    retry: false,
  });
}
