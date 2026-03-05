"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export function useScenarioLiveMarket() {
  return useQuery({
    queryKey: ["scenarioLiveMarket"],
    queryFn: () => api.getScenarioLiveMarket(),
    refetchInterval: 300000,
    staleTime: 120000,
  });
}
