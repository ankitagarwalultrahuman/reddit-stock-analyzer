"use client";

import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spinner } from "@/components/ui/loading";
import DataTable, { Column } from "@/components/ui/data-table";
import { useWeeklyPulse } from "@/lib/hooks/useScreener";
import { formatPrice, formatPercent } from "@/lib/utils";
import { Calendar } from "lucide-react";

const WATCHLISTS = [
  { value: "NIFTY50", label: "NIFTY 50" },
  { value: "NIFTY100", label: "NIFTY 100" },
  { value: "NIFTY_MIDCAP100", label: "Midcap 100" },
  { value: "NIFTY_SMALLCAP100", label: "Smallcap 100" },
  { value: "NIFTY_MIDSMALL", label: "Mid+Small (200)" },
];

const allStockColumns: Column<StockMetric>[] = [
  { key: "ticker", label: "Ticker", sortable: true, render: (r) => <span className="font-semibold">{r.ticker}</span> },
  { key: "sector", label: "Sector", render: (r) => <span className="text-xs">{r.sector}</span> },
  { key: "current_price", label: "Price", sortable: true, align: "right", render: (r) => formatPrice(r.current_price) },
  {
    key: "week_change_pct", label: "1W", sortable: true, align: "right",
    render: (r) => <span className={r.week_change_pct >= 0 ? "text-bullish" : "text-bearish"}>{formatPercent(r.week_change_pct)}</span>,
  },
  {
    key: "two_week_change_pct", label: "2W", sortable: true, align: "right",
    render: (r) => <span className={r.two_week_change_pct >= 0 ? "text-bullish" : "text-bearish"}>{formatPercent(r.two_week_change_pct)}</span>,
  },
  {
    key: "four_week_change_pct", label: "4W", sortable: true, align: "right",
    render: (r) => <span className={r.four_week_change_pct >= 0 ? "text-bullish" : "text-bearish"}>{formatPercent(r.four_week_change_pct)}</span>,
  },
  { key: "rsi", label: "RSI", sortable: true, align: "right", render: (r) => r.rsi?.toFixed(1) },
  {
    key: "technical_bias", label: "Bias", render: (r) => (
      <Badge variant={r.technical_bias === "bullish" ? "bullish" : r.technical_bias === "bearish" ? "bearish" : "neutral"}>
        {r.technical_bias}
      </Badge>
    ),
  },
  {
    key: "weekly_trend", label: "Trend", render: (r) => (
      <Badge variant={r.weekly_trend === "up" ? "bullish" : r.weekly_trend === "down" ? "bearish" : "neutral"}>
        {r.weekly_trend}
      </Badge>
    ),
  },
  { key: "relative_strength", label: "RS", sortable: true, align: "right", render: (r) => r.relative_strength?.toFixed(2) },
  {
    key: "week_52_high", label: "52W H", sortable: true, align: "right",
    render: (r) => r.week_52_high ? formatPrice(r.week_52_high) : "N/A",
  },
  {
    key: "week_52_low", label: "52W L", sortable: true, align: "right",
    render: (r) => r.week_52_low ? formatPrice(r.week_52_low) : "N/A",
  },
];

export default function WeeklyPage() {
  const pulse = useWeeklyPulse();
  const report = pulse.result as { report: WeeklyReport; summary: string } | null;
  const r = report?.report;

  return (
    <div className="space-y-6">
      <Header title="Weekly Pulse" subtitle="Weekly market breadth, trends, and key movers" />

      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Universe</label>
          <Select
            value={pulse.watchlist}
            onValueChange={(v) => pulse.setWatchlist(v)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WATCHLISTS.map((w) => (
                <SelectItem key={w.value} value={w.value}>{w.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          onClick={() => pulse.restart()}
          disabled={pulse.isRunning}
        >
          <Calendar className="mr-2 h-4 w-4" />
          {pulse.isRunning ? "Analyzing..." : "Generate Weekly Pulse"}
        </Button>
      </div>

      {pulse.isRunning && <Spinner className="py-12" />}
      {pulse.isError && (
        <Card><CardContent className="py-6 text-center text-destructive">Error: {pulse.error}</CardContent></Card>
      )}

      {r && (
        <>
          {/* NIFTY Metrics */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 1W</p>
                <p className={`text-2xl font-bold ${r.nifty_week_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_week_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 2W</p>
                <p className={`text-2xl font-bold ${r.nifty_two_week_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_two_week_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 4W</p>
                <p className={`text-2xl font-bold ${r.nifty_four_week_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_four_week_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">NIFTY 6W</p>
                <p className={`text-2xl font-bold ${r.nifty_month_change >= 0 ? "text-bullish" : "text-bearish"}`}>
                  {formatPercent(r.nifty_month_change)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Breadth</p>
                <p className="text-lg font-bold">
                  <span className="text-bullish">{r.market_breadth?.advances ?? 0}</span>
                  {" / "}
                  <span className="text-bearish">{r.market_breadth?.declines ?? 0}</span>
                  {" / "}
                  <span className="text-muted-foreground">{r.market_breadth?.unchanged ?? 0}</span>
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="overview">
            <TabsList className="flex-wrap">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="all">All Stocks ({r.all_stocks?.length ?? 0})</TabsTrigger>
              <TabsTrigger value="gainers">Gainers</TabsTrigger>
              <TabsTrigger value="losers">Losers</TabsTrigger>
              <TabsTrigger value="breakouts">Breakouts</TabsTrigger>
              <TabsTrigger value="breakdowns">Breakdowns</TabsTrigger>
              <TabsTrigger value="overbought">Overbought</TabsTrigger>
              <TabsTrigger value="oversold">Oversold</TabsTrigger>
              <TabsTrigger value="leaders">RS Leaders</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview">
              <div className="space-y-4">
                {/* Insights */}
                {r.insights && r.insights.length > 0 && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Key Insights</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {r.insights.map((insight: string, i: number) => (
                          <p key={i} className="text-sm">- {insight}</p>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
                {report?.summary && (
                  <Card>
                    <CardHeader><CardTitle className="text-base">Weekly Summary</CardTitle></CardHeader>
                    <CardContent>
                      <div className="whitespace-pre-wrap text-sm">{report.summary}</div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>

            {/* All Stocks Tab */}
            <TabsContent value="all">
              <DataTable
                data={(r.all_stocks ?? []) as StockMetric[]}
                columns={allStockColumns}
                defaultSortKey="week_change_pct"
                expandable={(row) => <StockDetail stock={row} />}
              />
            </TabsContent>

            <TabsContent value="gainers">
              <StockTable stocks={r.top_gainers} />
            </TabsContent>
            <TabsContent value="losers">
              <StockTable stocks={r.top_losers} />
            </TabsContent>
            <TabsContent value="breakouts">
              <StockTable stocks={r.breakout_candidates} />
            </TabsContent>
            <TabsContent value="breakdowns">
              <StockTable stocks={(r.all_stocks ?? []).filter((s: StockMetric) => s.breakdown_candidate)} emptyMsg="No breakdown candidates" />
            </TabsContent>
            <TabsContent value="overbought">
              <StockTable stocks={r.overbought_stocks} emptyMsg="No overbought stocks" />
            </TabsContent>
            <TabsContent value="oversold">
              <StockTable stocks={r.oversold_stocks} />
            </TabsContent>
            <TabsContent value="leaders">
              <StockTable stocks={r.rs_leaders} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

function StockDetail({ stock }: { stock: StockMetric }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5 text-sm">
      <div><span className="text-muted-foreground">4W Change:</span> <span className={stock.four_week_change_pct >= 0 ? "text-bullish" : "text-bearish"}>{formatPercent(stock.four_week_change_pct)}</span></div>
      <div><span className="text-muted-foreground">6W Change:</span> <span className={stock.month_change_pct >= 0 ? "text-bullish" : "text-bearish"}>{formatPercent(stock.month_change_pct)}</span></div>
      <div><span className="text-muted-foreground">MACD:</span> {stock.macd_signal}</div>
      <div><span className="text-muted-foreground">Volume:</span> {stock.volume_ratio?.toFixed(2)}x</div>
      <div><span className="text-muted-foreground">Support:</span> {formatPrice(stock.support_level)}</div>
      <div><span className="text-muted-foreground">Resistance:</span> {formatPrice(stock.resistance_level)}</div>
      <div><span className="text-muted-foreground">Trend Strength:</span> {stock.trend_strength}</div>
      <div><span className="text-muted-foreground">Consolidating:</span> {stock.consolidating ? "Yes" : "No"}</div>
      <div><span className="text-muted-foreground">52W from High:</span> {stock.pct_from_52w_high?.toFixed(1)}%</div>
      <div><span className="text-muted-foreground">Near 52W High:</span> {stock.near_52w_high ? "Yes" : "No"}</div>
    </div>
  );
}

function StockTable({ stocks, emptyMsg }: { stocks?: StockMetric[]; emptyMsg?: string }) {
  if (!stocks || stocks.length === 0) {
    return <Card><CardContent className="py-6 text-center text-muted-foreground">{emptyMsg || "No data"}</CardContent></Card>;
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
                <th className="pb-2 font-medium text-right">Price</th>
                <th className="pb-2 font-medium text-right">1W</th>
                <th className="pb-2 font-medium text-right">2W</th>
                <th className="pb-2 font-medium text-right">4W</th>
                <th className="pb-2 font-medium text-right">RSI</th>
                <th className="pb-2 font-medium">Bias</th>
                <th className="pb-2 font-medium text-right">RS</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => (
                <tr key={s.ticker} className="border-b">
                  <td className="py-2 font-semibold">{s.ticker}</td>
                  <td className="text-xs">{s.sector}</td>
                  <td className="text-right">{formatPrice(s.current_price)}</td>
                  <td className={`text-right ${s.week_change_pct >= 0 ? "text-bullish" : "text-bearish"}`}>
                    {formatPercent(s.week_change_pct)}
                  </td>
                  <td className={`text-right ${s.two_week_change_pct >= 0 ? "text-bullish" : "text-bearish"}`}>
                    {formatPercent(s.two_week_change_pct)}
                  </td>
                  <td className={`text-right ${s.four_week_change_pct >= 0 ? "text-bullish" : "text-bearish"}`}>
                    {formatPercent(s.four_week_change_pct)}
                  </td>
                  <td className="text-right">{s.rsi?.toFixed(1)}</td>
                  <td>
                    <Badge variant={s.technical_bias === "bullish" ? "bullish" : s.technical_bias === "bearish" ? "bearish" : "neutral"}>
                      {s.technical_bias}
                    </Badge>
                  </td>
                  <td className="text-right">{s.relative_strength?.toFixed(2)}</td>
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
  market_breadth: { advances: number; declines: number; unchanged: number };
  top_gainers: StockMetric[];
  top_losers: StockMetric[];
  breakout_candidates: StockMetric[];
  oversold_stocks: StockMetric[];
  overbought_stocks: StockMetric[];
  rs_leaders: StockMetric[];
  all_stocks: StockMetric[];
  insights: string[];
  [key: string]: unknown;
}

interface StockMetric {
  ticker: string;
  sector: string;
  current_price: number;
  week_change_pct: number;
  two_week_change_pct: number;
  four_week_change_pct: number;
  month_change_pct: number;
  volume_ratio: number;
  rsi: number;
  macd_signal: string;
  technical_bias: string;
  relative_strength: number;
  weekly_trend: string;
  trend_strength: string;
  consolidating: boolean;
  breakout_candidate: boolean;
  breakdown_candidate: boolean;
  support_level: number;
  resistance_level: number;
  week_52_high: number;
  week_52_low: number;
  pct_from_52w_high: number;
  near_52w_high: boolean;
  [key: string]: unknown;
}
