"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/loading";
import { useSectorAnalysis } from "@/lib/hooks/useScreener";
import { formatPercent, formatPrice } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PieChart as PieChartIcon, ChevronDown, ChevronRight } from "lucide-react";

export default function SectorsPage() {
  const sectorTask = useSectorAnalysis();
  const [expandedSector, setExpandedSector] = useState<string | null>(null);

  const result = sectorTask.result as {
    sectors: SectorData[];
    rotation_signals: RotationSignals;
    summary_table: SummaryRow[];
  } | null;

  return (
    <div className="space-y-6">
      <Header title="Sector Rotation" subtitle="Sector performance, momentum, and rotation signals" />

      <Button
        onClick={() => sectorTask.restart()}
        disabled={sectorTask.isRunning}
      >
        <PieChartIcon className="mr-2 h-4 w-4" />
        {sectorTask.isRunning ? "Analyzing..." : "Analyze Sectors"}
      </Button>

      {sectorTask.isRunning && <Spinner className="py-12" />}
      {sectorTask.isError && (
        <Card><CardContent className="py-6 text-center text-destructive">Error: {sectorTask.error}</CardContent></Card>
      )}

      {result && (
        <>
          {/* Overview */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Gaining Sectors</p>
                <p className="text-2xl font-bold text-bullish">
                  {result.sectors.filter((s) => s.momentum_trend === "gaining").length}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Losing Sectors</p>
                <p className="text-2xl font-bold text-bearish">
                  {result.sectors.filter((s) => s.momentum_trend === "losing").length}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Neutral Sectors</p>
                <p className="text-2xl font-bold text-neutral">
                  {result.sectors.filter((s) => s.momentum_trend === "neutral").length}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Rotation Signals */}
          {result.rotation_signals && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Rotation Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {result.rotation_signals.recommendations?.map((rec: string, i: number) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-primary">-</span>
                      <p className="text-sm">{rec}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Momentum Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sector Momentum</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart
                  data={[...result.sectors].sort((a, b) => b.momentum_score - a.momentum_score)}
                  layout="vertical"
                  margin={{ left: 100, right: 20 }}
                >
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis type="category" dataKey="sector" width={95} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => [Number(v).toFixed(1), "Momentum Score"]} />
                  <Bar dataKey="momentum_score" radius={[0, 4, 4, 0]}>
                    {[...result.sectors].sort((a, b) => b.momentum_score - a.momentum_score).map((s, i) => (
                      <Cell key={i} fill={s.momentum_trend === "gaining" ? "#22c55e" : s.momentum_trend === "losing" ? "#ef4444" : "#f59e0b"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Sector Rankings with Drill-Down */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sector Rankings (click to drill down)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 w-8" />
                      <th className="pb-2 font-medium">Sector</th>
                      <th className="pb-2 font-medium">Stocks</th>
                      <th className="pb-2 font-medium text-right">1W Return</th>
                      <th className="pb-2 font-medium text-right">1M Return</th>
                      <th className="pb-2 font-medium text-right">Avg RSI</th>
                      <th className="pb-2 font-medium text-right">Momentum</th>
                      <th className="pb-2 font-medium">Trend</th>
                      <th className="pb-2 font-medium text-right">Bullish/Bearish</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.sectors.map((s) => (
                      <>
                        <tr
                          key={s.sector}
                          className="border-b cursor-pointer hover:bg-muted/50"
                          onClick={() => setExpandedSector(expandedSector === s.sector ? null : s.sector)}
                        >
                          <td className="py-2">
                            {expandedSector === s.sector
                              ? <ChevronDown className="h-4 w-4" />
                              : <ChevronRight className="h-4 w-4" />
                            }
                          </td>
                          <td className="py-2 font-semibold">{s.sector}</td>
                          <td>{s.stock_count}</td>
                          <td className={`text-right ${s.avg_return_1w >= 0 ? "text-bullish" : "text-bearish"}`}>
                            {formatPercent(s.avg_return_1w)}
                          </td>
                          <td className={`text-right ${s.avg_return_1m >= 0 ? "text-bullish" : "text-bearish"}`}>
                            {formatPercent(s.avg_return_1m)}
                          </td>
                          <td className="text-right">{s.avg_rsi?.toFixed(1)}</td>
                          <td className="text-right">{s.momentum_score?.toFixed(1)}</td>
                          <td>
                            <Badge variant={s.momentum_trend === "gaining" ? "bullish" : s.momentum_trend === "losing" ? "bearish" : "neutral"}>
                              {s.momentum_trend}
                            </Badge>
                          </td>
                          <td className="text-right">
                            <span className="text-bullish">{s.bullish_count}</span>
                            {" / "}
                            <span className="text-bearish">{s.bearish_count}</span>
                          </td>
                        </tr>
                        {expandedSector === s.sector && s.stocks && (
                          <tr key={`${s.sector}-detail`} className="bg-muted/30">
                            <td colSpan={9} className="p-4">
                              <SectorStockTable stocks={s.stocks} />
                            </td>
                          </tr>
                        )}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function SectorStockTable({ stocks }: { stocks: StockPerf[] }) {
  const [sortKey, setSortKey] = useState<string>("return_1m");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = [...stocks].sort((a, b) => {
    const av = (a as unknown as Record<string, number>)[sortKey] ?? 0;
    const bv = (b as unknown as Record<string, number>)[sortKey] ?? 0;
    return sortDir === "asc" ? av - bv : bv - av;
  });

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const sortHeader = (key: string, label: string) => (
    <th
      className="pb-2 font-medium text-right cursor-pointer hover:text-foreground select-none"
      onClick={() => handleSort(key)}
    >
      {label} {sortKey === key ? (sortDir === "asc" ? "^" : "v") : ""}
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="pb-2 font-medium">Ticker</th>
            <th className="pb-2 font-medium text-right">Price</th>
            {sortHeader("return_1w", "1W")}
            {sortHeader("return_1m", "1M")}
            {sortHeader("return_2m", "2M")}
            {sortHeader("return_3m", "3M")}
            {sortHeader("rsi", "RSI")}
            <th className="pb-2 font-medium">Bias</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((st) => (
            <tr key={st.ticker} className="border-b">
              <td className="py-1.5 font-semibold">{st.ticker}</td>
              <td className="text-right">{formatPrice(st.current_price)}</td>
              <td className={`text-right ${st.return_1w >= 0 ? "text-bullish" : "text-bearish"}`}>{formatPercent(st.return_1w)}</td>
              <td className={`text-right ${st.return_1m >= 0 ? "text-bullish" : "text-bearish"}`}>{formatPercent(st.return_1m)}</td>
              <td className={`text-right ${st.return_2m >= 0 ? "text-bullish" : "text-bearish"}`}>{formatPercent(st.return_2m)}</td>
              <td className={`text-right ${st.return_3m >= 0 ? "text-bullish" : "text-bearish"}`}>{formatPercent(st.return_3m)}</td>
              <td className="text-right">{st.rsi?.toFixed(1) ?? "N/A"}</td>
              <td>
                <Badge variant={st.technical_bias === "bullish" ? "bullish" : st.technical_bias === "bearish" ? "bearish" : "neutral"}>
                  {st.technical_bias}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface StockPerf {
  ticker: string;
  current_price: number;
  return_1w: number;
  return_1m: number;
  return_2m: number;
  return_3m: number;
  return_6m: number;
  rsi: number | null;
  technical_bias: string;
}

interface SectorData {
  sector: string;
  stock_count: number;
  avg_return_1w: number;
  avg_return_1m: number;
  avg_rsi: number;
  momentum_score: number;
  momentum_trend: string;
  bullish_count: number;
  bearish_count: number;
  stocks: StockPerf[];
}

interface RotationSignals {
  recommendations: string[];
  [key: string]: unknown;
}

interface SummaryRow {
  [key: string]: unknown;
}
