"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/loading";
import { useSectorAnalysis } from "@/lib/hooks/useScreener";
import { formatPercent } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from "recharts";
import { CalendarDays, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";

export default function MonthlyPage() {
  const [timeframe, setTimeframe] = useState<"1m" | "2m" | "3m" | "6m">("1m");
  const sectorTask = useSectorAnalysis();

  const result = sectorTask.result as {
    sectors: SectorMonthly[];
    rotation_signals: RotationSignals;
  } | null;

  const returnKey = {
    "1m": "avg_return_1m",
    "2m": "avg_return_2m",
    "3m": "avg_return_3m",
    "6m": "avg_return_6m",
  }[timeframe] as keyof SectorMonthly;

  const chartData = result?.sectors
    .map((s) => ({
      sector: s.sector,
      return_pct: Number(s[returnKey]) || 0,
    }))
    .sort((a, b) => b.return_pct - a.return_pct) ?? [];

  // Derive trade ideas from sector data
  const tradeIdeas = result ? generateTradeIdeas(result.sectors, result.rotation_signals) : null;

  return (
    <div className="space-y-6">
      <Header title="Monthly Rotation" subtitle="Sector performance over longer timeframes" />

      <div className="flex items-center gap-4">
        <Button
          onClick={() => sectorTask.restart()}
          disabled={sectorTask.isRunning}
        >
          <CalendarDays className="mr-2 h-4 w-4" />
          {sectorTask.isRunning ? "Analyzing..." : "Analyze Sectors"}
        </Button>

        <div className="flex gap-1">
          {(["1m", "2m", "3m", "6m"] as const).map((tf) => (
            <Button
              key={tf}
              variant={timeframe === tf ? "default" : "outline"}
              size="sm"
              onClick={() => setTimeframe(tf)}
            >
              {tf.toUpperCase()}
            </Button>
          ))}
        </div>
      </div>

      {sectorTask.isRunning && <Spinner className="py-12" />}

      {result && (
        <>
          {/* Trade Ideas Section */}
          {tradeIdeas && (
            <div className="grid gap-4 sm:grid-cols-3">
              {/* Best for Longs */}
              <Card className="border-green-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-bullish">
                    <TrendingUp className="h-4 w-4" />
                    Best Sectors for Longs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {tradeIdeas.bestForLongs.map((s) => (
                      <div key={s.sector} className="flex items-center justify-between text-sm">
                        <span className="font-medium">{s.sector}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-bullish">{formatPercent(s.return_pct)}</span>
                          <Badge variant="bullish" className="text-xs">{s.momentum_trend}</Badge>
                        </div>
                      </div>
                    ))}
                    {tradeIdeas.bestForLongs.length === 0 && (
                      <p className="text-sm text-muted-foreground">No strong long candidates</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Sectors to Avoid */}
              <Card className="border-red-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-bearish">
                    <TrendingDown className="h-4 w-4" />
                    Sectors to Avoid
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {tradeIdeas.toAvoid.map((s) => (
                      <div key={s.sector} className="flex items-center justify-between text-sm">
                        <span className="font-medium">{s.sector}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-bearish">{formatPercent(s.return_pct)}</span>
                          <Badge variant="bearish" className="text-xs">{s.momentum_trend}</Badge>
                        </div>
                      </div>
                    ))}
                    {tradeIdeas.toAvoid.length === 0 && (
                      <p className="text-sm text-muted-foreground">No sectors flagged</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Contrarian / Oversold */}
              <Card className="border-amber-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-amber-600">
                    <AlertTriangle className="h-4 w-4" />
                    Contrarian Plays (Oversold)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {tradeIdeas.contrarian.map((s) => (
                      <div key={s.sector} className="flex items-center justify-between text-sm">
                        <span className="font-medium">{s.sector}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">RSI {s.avg_rsi?.toFixed(0)}</span>
                          <Badge variant="neutral" className="text-xs">oversold</Badge>
                        </div>
                      </div>
                    ))}
                    {tradeIdeas.contrarian.length === 0 && (
                      <p className="text-sm text-muted-foreground">No oversold sectors</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Overbought Warning */}
          {tradeIdeas && tradeIdeas.overbought.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Overbought Sectors (Caution)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-3">
                  {tradeIdeas.overbought.map((s) => (
                    <div key={s.sector} className="flex items-center gap-2 text-sm">
                      <Badge variant="bearish" className="text-xs">{s.sector}</Badge>
                      <span>RSI {s.avg_rsi?.toFixed(0)}</span>
                      <span className="text-bullish">{formatPercent(s.avg_return_1m)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sector Returns ({timeframe.toUpperCase()})</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tickFormatter={(v) => `${v.toFixed(1)}%`} />
                  <YAxis type="category" dataKey="sector" width={95} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}%`, "Return"]} />
                  <Bar dataKey="return_pct" radius={[0, 4, 4, 0]}>
                    {chartData.map((d, i) => (
                      <Cell key={i} fill={d.return_pct >= 0 ? "#22c55e" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Rotation Signals */}
          {result.rotation_signals?.recommendations && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Rotation Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {result.rotation_signals.recommendations.map((rec: string, i: number) => (
                    <p key={i} className="text-sm">- {rec}</p>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Performance Matrix */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Performance Matrix</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium">Sector</th>
                      <th className="pb-2 font-medium text-right">1M</th>
                      <th className="pb-2 font-medium text-right">2M</th>
                      <th className="pb-2 font-medium text-right">3M</th>
                      <th className="pb-2 font-medium text-right">6M</th>
                      <th className="pb-2 font-medium text-right">RSI</th>
                      <th className="pb-2 font-medium">Momentum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.sectors.map((s) => (
                      <tr key={s.sector} className="border-b">
                        <td className="py-2 font-semibold">{s.sector}</td>
                        <td className={`text-right ${s.avg_return_1m >= 0 ? "text-bullish" : "text-bearish"}`}>
                          {formatPercent(s.avg_return_1m)}
                        </td>
                        <td className={`text-right ${s.avg_return_2m >= 0 ? "text-bullish" : "text-bearish"}`}>
                          {formatPercent(s.avg_return_2m)}
                        </td>
                        <td className={`text-right ${s.avg_return_3m >= 0 ? "text-bullish" : "text-bearish"}`}>
                          {formatPercent(s.avg_return_3m)}
                        </td>
                        <td className={`text-right ${s.avg_return_6m >= 0 ? "text-bullish" : "text-bearish"}`}>
                          {formatPercent(s.avg_return_6m)}
                        </td>
                        <td className="text-right">{s.avg_rsi?.toFixed(1)}</td>
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

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function generateTradeIdeas(sectors: SectorMonthly[], signals: RotationSignals) {
  const sorted = [...sectors].sort((a, b) => b.avg_return_1m - a.avg_return_1m);

  // Best for longs: gaining momentum + positive returns
  const bestForLongs = sorted
    .filter((s) => s.momentum_trend === "gaining" && s.avg_return_1m > 0)
    .slice(0, 3)
    .map((s) => ({ sector: s.sector, return_pct: s.avg_return_1m, momentum_trend: s.momentum_trend }));

  // Sectors to avoid: losing momentum + negative returns
  const toAvoid = [...sorted]
    .reverse()
    .filter((s) => s.momentum_trend === "losing" && s.avg_return_1m < 0)
    .slice(0, 3)
    .map((s) => ({ sector: s.sector, return_pct: s.avg_return_1m, momentum_trend: s.momentum_trend }));

  // Contrarian: oversold (RSI < 40)
  const contrarian = sectors
    .filter((s) => s.avg_rsi < 40)
    .sort((a, b) => a.avg_rsi - b.avg_rsi)
    .slice(0, 3);

  // Overbought: RSI > 65
  const overbought = sectors
    .filter((s) => s.avg_rsi > 65)
    .sort((a, b) => b.avg_rsi - a.avg_rsi)
    .slice(0, 3);

  return { bestForLongs, toAvoid, contrarian, overbought };
}

interface SectorMonthly {
  sector: string;
  avg_return_1m: number;
  avg_return_2m: number;
  avg_return_3m: number;
  avg_return_6m: number;
  avg_rsi: number;
  momentum_trend: string;
  momentum_score: number;
}

interface RotationSignals {
  recommendations: string[];
  [key: string]: unknown;
}
