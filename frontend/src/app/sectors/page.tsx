"use client";

import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/loading";
import { useSectorAnalysis } from "@/lib/hooks/useScreener";
import { formatPercent } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PieChart as PieChartIcon } from "lucide-react";

export default function SectorsPage() {
  const sectorTask = useSectorAnalysis();

  const result = sectorTask.result as {
    sectors: SectorData[];
    rotation_signals: RotationSignals;
    summary_table: SummaryRow[];
  } | null;

  return (
    <div className="space-y-6">
      <Header title="Sector Rotation" subtitle="Sector performance, momentum, and rotation signals" />

      <Button
        onClick={() => { sectorTask.reset(); setTimeout(() => sectorTask.start(), 0); }}
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
                  data={result.sectors.sort((a, b) => b.momentum_score - a.momentum_score)}
                  layout="vertical"
                  margin={{ left: 100, right: 20 }}
                >
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis type="category" dataKey="sector" width={95} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => [Number(v).toFixed(1), "Momentum Score"]} />
                  <Bar dataKey="momentum_score" radius={[0, 4, 4, 0]}>
                    {result.sectors.map((s, i) => (
                      <Cell key={i} fill={s.momentum_trend === "gaining" ? "#22c55e" : s.momentum_trend === "losing" ? "#ef4444" : "#f59e0b"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Rankings Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sector Rankings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium">Sector</th>
                      <th className="pb-2 font-medium">Stocks</th>
                      <th className="pb-2 font-medium">1W Return</th>
                      <th className="pb-2 font-medium">1M Return</th>
                      <th className="pb-2 font-medium">Avg RSI</th>
                      <th className="pb-2 font-medium">Momentum</th>
                      <th className="pb-2 font-medium">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.sectors.map((s) => (
                      <tr key={s.sector} className="border-b">
                        <td className="py-2 font-semibold">{s.sector}</td>
                        <td>{s.stock_count}</td>
                        <td className={s.avg_return_1w >= 0 ? "text-bullish" : "text-bearish"}>
                          {formatPercent(s.avg_return_1w)}
                        </td>
                        <td className={s.avg_return_1m >= 0 ? "text-bullish" : "text-bearish"}>
                          {formatPercent(s.avg_return_1m)}
                        </td>
                        <td>{s.avg_rsi?.toFixed(1)}</td>
                        <td>{s.momentum_score?.toFixed(1)}</td>
                        <td>
                          <Badge variant={s.momentum_trend === "gaining" ? "bullish" : s.momentum_trend === "losing" ? "bearish" : "neutral"}>
                            {s.momentum_trend}
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

interface SectorData {
  sector: string;
  stock_count: number;
  avg_return_1w: number;
  avg_return_1m: number;
  avg_rsi: number;
  momentum_score: number;
  momentum_trend: string;
}

interface RotationSignals {
  recommendations: string[];
  [key: string]: unknown;
}

interface SummaryRow {
  [key: string]: unknown;
}
