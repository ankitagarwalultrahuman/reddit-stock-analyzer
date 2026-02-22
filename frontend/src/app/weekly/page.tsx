"use client";

import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spinner } from "@/components/ui/loading";
import { useWeeklyPulse } from "@/lib/hooks/useScreener";
import { formatPrice, formatPercent } from "@/lib/utils";
import { Calendar } from "lucide-react";

export default function WeeklyPage() {
  const pulse = useWeeklyPulse();
  const report = pulse.result as { report: WeeklyReport; summary: string } | null;
  const r = report?.report;

  return (
    <div className="space-y-6">
      <Header title="Weekly Pulse" subtitle="Weekly market breadth, trends, and key movers" />

      <Button
        onClick={() => { pulse.reset(); setTimeout(() => pulse.start(), 0); }}
        disabled={pulse.isRunning}
      >
        <Calendar className="mr-2 h-4 w-4" />
        {pulse.isRunning ? "Analyzing..." : "Generate Weekly Pulse"}
      </Button>

      {pulse.isRunning && <Spinner className="py-12" />}
      {pulse.isError && (
        <Card><CardContent className="py-6 text-center text-destructive">Error: {pulse.error}</CardContent></Card>
      )}

      {r && (
        <>
          {/* NIFTY Metrics */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 1W Change</p>
                <p className={`text-2xl font-bold ${r.nifty_week_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_week_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 2W Change</p>
                <p className={`text-2xl font-bold ${r.nifty_two_week_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_two_week_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 4W Change</p>
                <p className={`text-2xl font-bold ${r.nifty_four_week_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_four_week_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Market Breadth</p>
                <p className="text-lg font-bold">
                  <span className="text-bullish">{r.market_breadth?.advancing ?? 0}</span>
                  {" / "}
                  <span className="text-bearish">{r.market_breadth?.declining ?? 0}</span>
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="gainers">
            <TabsList>
              <TabsTrigger value="gainers">Top Gainers</TabsTrigger>
              <TabsTrigger value="losers">Top Losers</TabsTrigger>
              <TabsTrigger value="breakouts">Breakout Candidates</TabsTrigger>
              <TabsTrigger value="oversold">Oversold</TabsTrigger>
              <TabsTrigger value="leaders">RS Leaders</TabsTrigger>
            </TabsList>

            <TabsContent value="gainers">
              <StockTable stocks={r.top_gainers} />
            </TabsContent>
            <TabsContent value="losers">
              <StockTable stocks={r.top_losers} />
            </TabsContent>
            <TabsContent value="breakouts">
              <StockTable stocks={r.breakout_candidates} />
            </TabsContent>
            <TabsContent value="oversold">
              <StockTable stocks={r.oversold_stocks} />
            </TabsContent>
            <TabsContent value="leaders">
              <StockTable stocks={r.rs_leaders} />
            </TabsContent>
          </Tabs>

          {/* Summary */}
          {report?.summary && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Weekly Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm">{report.summary}</div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function StockTable({ stocks }: { stocks?: StockMetric[] }) {
  if (!stocks || stocks.length === 0) {
    return <Card><CardContent className="py-6 text-center text-muted-foreground">No data</CardContent></Card>;
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-2 font-medium">Ticker</th>
                <th className="pb-2 font-medium">Sector</th>
                <th className="pb-2 font-medium">Price</th>
                <th className="pb-2 font-medium">1W</th>
                <th className="pb-2 font-medium">2W</th>
                <th className="pb-2 font-medium">RSI</th>
                <th className="pb-2 font-medium">Bias</th>
                <th className="pb-2 font-medium">RS</th>
              </tr>
            </thead>
            <tbody>
              {stocks.slice(0, 15).map((s) => (
                <tr key={s.ticker} className="border-b">
                  <td className="py-2 font-semibold">{s.ticker}</td>
                  <td className="text-xs">{s.sector}</td>
                  <td>{formatPrice(s.current_price)}</td>
                  <td className={s.week_change_pct >= 0 ? "text-bullish" : "text-bearish"}>
                    {formatPercent(s.week_change_pct)}
                  </td>
                  <td className={s.two_week_change_pct >= 0 ? "text-bullish" : "text-bearish"}>
                    {formatPercent(s.two_week_change_pct)}
                  </td>
                  <td>{s.rsi?.toFixed(1)}</td>
                  <td>
                    <Badge variant={s.technical_bias === "bullish" ? "bullish" : s.technical_bias === "bearish" ? "bearish" : "neutral"}>
                      {s.technical_bias}
                    </Badge>
                  </td>
                  <td>{s.relative_strength?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

interface WeeklyReport {
  nifty_week_change: number;
  nifty_two_week_change: number;
  nifty_four_week_change: number;
  nifty_month_change: number;
  market_breadth: { advancing: number; declining: number; unchanged: number };
  top_gainers: StockMetric[];
  top_losers: StockMetric[];
  breakout_candidates: StockMetric[];
  oversold_stocks: StockMetric[];
  rs_leaders: StockMetric[];
  [key: string]: unknown;
}

interface StockMetric {
  ticker: string;
  sector: string;
  current_price: number;
  week_change_pct: number;
  two_week_change_pct: number;
  rsi: number;
  technical_bias: string;
  relative_strength: number;
}
