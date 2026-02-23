"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/loading";
import { useETFAnalysis } from "@/lib/hooks/useScreener";
import { formatPercent, formatPrice } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Layers } from "lucide-react";

interface ETFData {
  ticker: string;
  name: string;
  category: string;
  current_price: number;
  return_1w: number;
  return_1m: number;
  return_3m: number;
  return_6m: number;
  rs_1w: number;
  rs_1m: number;
  rs_3m: number;
  rs_6m: number;
  rsi: number | null;
  rsi_signal: string | null;
  macd_trend: string | null;
  ma_trend: string | null;
  price_vs_ema20: string | null;
  price_vs_ema50: string | null;
  price_vs_ema200: string | null;
  volume_signal: string | null;
  adx: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  pct_from_52w_high: number | null;
  pct_from_52w_low: number | null;
  atr_percent: number | null;
  volatility_level: string | null;
  momentum_score: number;
  technical_score: number | null;
  technical_bias: string | null;
  rank: number;
}

interface ETFSummary {
  top_momentum: [string, string, number][];
  bottom_momentum: [string, string, number][];
  outperforming_nifty_count: number;
  oversold_count: number;
  near_52w_high_count: number;
  near_52w_low_count: number;
  avg_momentum: number;
  category_best: Record<string, string>;
  recommendations: string[];
  total_etfs: number;
}

export default function ETFPage() {
  const etfTask = useETFAnalysis();
  const [sortKey, setSortKey] = useState<string>("momentum_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const result = etfTask.result as {
    etfs: ETFData[];
    summary: ETFSummary;
  } | null;

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortedETFs = result
    ? [...result.etfs].sort((a, b) => {
        const av = (a as unknown as Record<string, number>)[sortKey] ?? 0;
        const bv = (b as unknown as Record<string, number>)[sortKey] ?? 0;
        return sortDir === "asc" ? av - bv : bv - av;
      })
    : [];

  const sortHeader = (key: string, label: string, align = "text-right") => (
    <th
      className={`pb-2 font-medium ${align} cursor-pointer hover:text-foreground select-none whitespace-nowrap`}
      onClick={() => handleSort(key)}
    >
      {label} {sortKey === key ? (sortDir === "asc" ? "↑" : "↓") : ""}
    </th>
  );

  return (
    <div className="space-y-6">
      <Header
        title="Sector ETF Analysis"
        subtitle="Multi-timeframe performance and relative strength vs NIFTY for sector ETFs"
      />

      <Button
        onClick={() => etfTask.restart()}
        disabled={etfTask.isRunning}
      >
        <Layers className="mr-2 h-4 w-4" />
        {etfTask.isRunning ? "Analyzing..." : "Analyze ETFs"}
      </Button>

      {etfTask.isRunning && <Spinner className="py-12" />}
      {etfTask.isError && (
        <Card>
          <CardContent className="py-6 text-center text-destructive">
            Error: {etfTask.error}
          </CardContent>
        </Card>
      )}

      {result && (
        <>
          {/* Summary Cards */}
          <div className="grid gap-4 sm:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Top Momentum</p>
                <p className="text-2xl font-bold">
                  {result.summary.top_momentum[0]?.[0] ?? "N/A"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Score: {result.summary.top_momentum[0]?.[2]?.toFixed(0) ?? "-"}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Outperforming NIFTY</p>
                <p className="text-2xl font-bold text-bullish">
                  {result.summary.outperforming_nifty_count}
                  <span className="text-sm text-muted-foreground font-normal">
                    /{result.summary.total_etfs}
                  </span>
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Oversold ETFs</p>
                <p className="text-2xl font-bold text-bearish">
                  {result.summary.oversold_count}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Avg Momentum</p>
                <p className="text-2xl font-bold">
                  {result.summary.avg_momentum.toFixed(0)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Recommendations */}
          {result.summary.recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {result.summary.recommendations.map((rec, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-primary">-</span>
                      <p className="text-sm">{rec}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Momentum Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Momentum Score</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={Math.max(300, result.etfs.length * 36)}>
                <BarChart
                  data={[...result.etfs].sort(
                    (a, b) => b.momentum_score - a.momentum_score
                  )}
                  layout="vertical"
                  margin={{ left: 120, right: 20 }}
                >
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis
                    type="category"
                    dataKey="ticker"
                    width={115}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    formatter={(v) => [Number(v).toFixed(1), "Momentum"]}
                  />
                  <Bar dataKey="momentum_score" radius={[0, 4, 4, 0]}>
                    {[...result.etfs]
                      .sort((a, b) => b.momentum_score - a.momentum_score)
                      .map((etf, i) => (
                        <Cell
                          key={i}
                          fill={
                            etf.momentum_score > 60
                              ? "#22c55e"
                              : etf.momentum_score < 40
                              ? "#ef4444"
                              : "#f59e0b"
                          }
                        />
                      ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* RS Heatmap */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Relative Strength vs NIFTY
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium">ETF</th>
                      <th className="pb-2 font-medium text-center">1W</th>
                      <th className="pb-2 font-medium text-center">1M</th>
                      <th className="pb-2 font-medium text-center">3M</th>
                      <th className="pb-2 font-medium text-center">6M</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...result.etfs]
                      .sort((a, b) => b.rs_1m - a.rs_1m)
                      .map((etf) => (
                        <tr key={etf.ticker} className="border-b">
                          <td className="py-1.5 font-semibold">{etf.ticker}</td>
                          {(
                            [
                              ["rs_1w", etf.rs_1w],
                              ["rs_1m", etf.rs_1m],
                              ["rs_3m", etf.rs_3m],
                              ["rs_6m", etf.rs_6m],
                            ] as [string, number][]
                          ).map(([key, val]) => (
                            <td
                              key={key}
                              className={`text-center py-1.5 font-medium ${
                                val > 0
                                  ? "bg-green-500/15 text-bullish"
                                  : val < 0
                                  ? "bg-red-500/15 text-bearish"
                                  : ""
                              }`}
                            >
                              {val >= 0 ? "+" : ""}
                              {val.toFixed(1)}%
                            </td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Main Data Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">ETF Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium">#</th>
                      <th className="pb-2 font-medium">Ticker</th>
                      <th className="pb-2 font-medium">Category</th>
                      {sortHeader("current_price", "Price")}
                      {sortHeader("return_1w", "1W%")}
                      {sortHeader("return_1m", "1M%")}
                      {sortHeader("return_3m", "3M%")}
                      {sortHeader("return_6m", "6M%")}
                      {sortHeader("rs_1m", "RS 1M")}
                      {sortHeader("rsi", "RSI")}
                      <th className="pb-2 font-medium text-right">MACD</th>
                      <th className="pb-2 font-medium text-right">MA Trend</th>
                      {sortHeader("pct_from_52w_high", "% 52W H")}
                      {sortHeader("momentum_score", "Momentum")}
                      <th className="pb-2 font-medium">Bias</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedETFs.map((etf) => (
                      <tr key={etf.ticker} className="border-b">
                        <td className="py-2 text-muted-foreground">{etf.rank}</td>
                        <td className="py-2 font-semibold">{etf.ticker}</td>
                        <td className="py-2 text-muted-foreground text-xs">
                          {etf.category}
                        </td>
                        <td className="text-right">{formatPrice(etf.current_price)}</td>
                        <td
                          className={`text-right ${
                            etf.return_1w >= 0 ? "text-bullish" : "text-bearish"
                          }`}
                        >
                          {formatPercent(etf.return_1w)}
                        </td>
                        <td
                          className={`text-right ${
                            etf.return_1m >= 0 ? "text-bullish" : "text-bearish"
                          }`}
                        >
                          {formatPercent(etf.return_1m)}
                        </td>
                        <td
                          className={`text-right ${
                            etf.return_3m >= 0 ? "text-bullish" : "text-bearish"
                          }`}
                        >
                          {formatPercent(etf.return_3m)}
                        </td>
                        <td
                          className={`text-right ${
                            etf.return_6m >= 0 ? "text-bullish" : "text-bearish"
                          }`}
                        >
                          {formatPercent(etf.return_6m)}
                        </td>
                        <td
                          className={`text-right font-medium ${
                            etf.rs_1m > 0 ? "text-bullish" : "text-bearish"
                          }`}
                        >
                          {etf.rs_1m >= 0 ? "+" : ""}
                          {etf.rs_1m.toFixed(1)}
                        </td>
                        <td className="text-right">{etf.rsi?.toFixed(1) ?? "N/A"}</td>
                        <td className="text-right text-xs">{etf.macd_trend ?? "N/A"}</td>
                        <td className="text-right text-xs">{etf.ma_trend ?? "N/A"}</td>
                        <td className="text-right">
                          {etf.pct_from_52w_high != null
                            ? `${etf.pct_from_52w_high.toFixed(1)}%`
                            : "N/A"}
                        </td>
                        <td className="text-right font-bold">
                          {etf.momentum_score.toFixed(0)}
                        </td>
                        <td>
                          <Badge
                            variant={
                              etf.technical_bias === "bullish"
                                ? "bullish"
                                : etf.technical_bias === "bearish"
                                ? "bearish"
                                : "neutral"
                            }
                          >
                            {etf.technical_bias ?? "N/A"}
                          </Badge>
                        </td>
                      </tr>
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
