"use client";

import { useState, useMemo } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LoadingSection } from "@/components/ui/loading";
import PriceLineChart from "@/components/charts/PriceLineChart";
import { useStockHistory } from "@/lib/hooks/useStocks";
import { useHoldings } from "@/lib/hooks/usePortfolio";
import { useStockMentions, useReportDates } from "@/lib/hooks/useReport";
import { formatPrice, formatPercent } from "@/lib/utils";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const POPULAR_STOCKS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"];
const COMPARISON_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"];

export default function HistoryPage() {
  const [selectedTickers, setSelectedTickers] = useState<string[]>(["RELIANCE"]);
  const [days, setDays] = useState(30);
  const [customTicker, setCustomTicker] = useState("");
  const [compareMode, setCompareMode] = useState(false);
  const { data: holdings } = useHoldings();
  const { data: dates } = useReportDates();
  const { data: stocks } = useStockMentions(dates?.[0] ?? null);

  // Single stock history
  const { data: historyData, isLoading } = useStockHistory(
    !compareMode ? selectedTickers[0] ?? null : null,
    days
  );

  // Multi-stock history
  const { data: multiData, isLoading: multiLoading } = useQuery({
    queryKey: ["multiStock", selectedTickers, days],
    queryFn: () => api.getMultipleStocks(selectedTickers, days),
    enabled: compareMode && selectedTickers.length > 1,
  });

  const chartData = historyData?.map((r) => ({
    date: (r.Date || r.index || "").slice(5),
    close: r.Close,
  })) ?? [];

  // Normalized comparison data (base 100)
  const normalizedData = useMemo(() => {
    if (!multiData || selectedTickers.length < 2) return [];

    // Find common dates
    const firstTicker = selectedTickers[0];
    const baseData = multiData[firstTicker];
    if (!baseData || baseData.length === 0) return [];

    return baseData.map((row, i) => {
      const point: Record<string, unknown> = {
        date: ((row as unknown as Record<string, unknown>).Date as string || "").slice(5),
      };
      for (const ticker of selectedTickers) {
        const tickerData = multiData[ticker];
        if (tickerData && tickerData.length > i && tickerData[0]?.Close) {
          point[ticker] = ((tickerData[i]?.Close / tickerData[0].Close) * 100);
        }
      }
      return point;
    });
  }, [multiData, selectedTickers]);

  // Performance metrics for comparison
  const comparisonMetrics = useMemo(() => {
    if (!multiData) return [];
    return selectedTickers.map((ticker) => {
      const d = multiData[ticker];
      if (!d || d.length < 2) return { ticker, totalReturn: 0, periodHigh: 0, periodLow: 0, volatility: 0, maxDrawdown: 0 };

      const closes = d.map((r) => r.Close);
      const totalReturn = ((closes[closes.length - 1] - closes[0]) / closes[0]) * 100;
      const periodHigh = Math.max(...d.map((r) => r.High));
      const periodLow = Math.min(...d.map((r) => r.Low));

      // Simple volatility (std dev of daily returns)
      const returns = closes.slice(1).map((c, i) => (c - closes[i]) / closes[i]);
      const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
      const variance = returns.reduce((a, b) => a + (b - mean) ** 2, 0) / returns.length;
      const dailyVol = Math.sqrt(variance);
      const annVol = dailyVol * Math.sqrt(252) * 100;

      // Max drawdown
      let peak = closes[0];
      let maxDd = 0;
      for (const c of closes) {
        if (c > peak) peak = c;
        const dd = ((peak - c) / peak) * 100;
        if (dd > maxDd) maxDd = dd;
      }

      return { ticker, totalReturn, periodHigh, periodLow, volatility: annVol, maxDrawdown: maxDd };
    });
  }, [multiData, selectedTickers]);

  const toggleTicker = (t: string) => {
    if (compareMode) {
      if (selectedTickers.includes(t)) {
        if (selectedTickers.length > 1) setSelectedTickers(selectedTickers.filter((x) => x !== t));
      } else if (selectedTickers.length < 5) {
        setSelectedTickers([...selectedTickers, t]);
      }
    } else {
      setSelectedTickers([t]);
    }
  };

  return (
    <div className="space-y-6">
      <Header title="Historic Performance" subtitle="Track stock price history and compare performance" />

      {/* Compare Mode Toggle */}
      <div className="flex items-center gap-3">
        <Button
          variant={compareMode ? "default" : "outline"}
          size="sm"
          onClick={() => {
            setCompareMode(!compareMode);
            if (!compareMode && selectedTickers.length === 1) {
              // Keep current + add a second
            }
          }}
        >
          {compareMode ? "Comparing" : "Compare Mode"}
        </Button>
        {compareMode && (
          <span className="text-sm text-muted-foreground">
            Select up to 5 stocks ({selectedTickers.length}/5)
          </span>
        )}
      </div>

      {/* Stock Selection */}
      <Tabs defaultValue="popular">
        <TabsList>
          <TabsTrigger value="popular">Popular</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="reddit">Reddit Picks</TabsTrigger>
          <TabsTrigger value="custom">Custom</TabsTrigger>
        </TabsList>

        <TabsContent value="popular">
          <div className="flex flex-wrap gap-2 py-2">
            {POPULAR_STOCKS.map((t) => (
              <Button
                key={t}
                variant={selectedTickers.includes(t) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleTicker(t)}
              >
                {t}
              </Button>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="portfolio">
          <div className="flex flex-wrap gap-2 py-2">
            {holdings?.map((h) => (
              <Button
                key={h.ticker}
                variant={selectedTickers.includes(h.ticker) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleTicker(h.ticker)}
              >
                {h.ticker}
              </Button>
            ))}
            {(!holdings || holdings.length === 0) && (
              <p className="text-sm text-muted-foreground">No portfolio holdings</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="reddit">
          <div className="flex flex-wrap gap-2 py-2">
            {stocks?.slice(0, 10).map((s) => (
              <Button
                key={s.ticker}
                variant={selectedTickers.includes(s.ticker) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleTicker(s.ticker)}
              >
                {s.ticker}
              </Button>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="custom">
          <div className="flex items-center gap-2 py-2">
            <input
              className="flex h-9 w-32 rounded-md border border-input bg-background px-3 py-1 text-sm"
              value={customTicker}
              onChange={(e) => setCustomTicker(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && customTicker) {
                  toggleTicker(customTicker.toUpperCase());
                  setCustomTicker("");
                }
              }}
              placeholder="Enter ticker"
            />
            <Button
              size="sm"
              onClick={() => {
                if (customTicker) {
                  toggleTicker(customTicker.toUpperCase());
                  setCustomTicker("");
                }
              }}
            >
              Add
            </Button>
          </div>
        </TabsContent>
      </Tabs>

      {/* Selected tickers pills (compare mode) */}
      {compareMode && selectedTickers.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedTickers.map((t, i) => (
            <Badge
              key={t}
              variant="secondary"
              className="cursor-pointer"
              style={{ borderLeft: `3px solid ${COMPARISON_COLORS[i]}` }}
              onClick={() => {
                if (selectedTickers.length > 1) setSelectedTickers(selectedTickers.filter((x) => x !== t));
              }}
            >
              {t} x
            </Badge>
          ))}
        </div>
      )}

      {/* Timeframe */}
      <div className="flex gap-2">
        {[7, 14, 30, 60, 90, 180, 365].map((d) => (
          <Button
            key={d}
            variant={days === d ? "default" : "outline"}
            size="sm"
            onClick={() => setDays(d)}
          >
            {d}d
          </Button>
        ))}
      </div>

      {/* Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {compareMode && selectedTickers.length > 1
              ? `Normalized Comparison (Base 100) - ${days} Days`
              : `${selectedTickers.join(", ")} - ${days} Day Chart`
            }
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(isLoading || multiLoading) ? (
            <LoadingSection />
          ) : compareMode && selectedTickers.length > 1 && normalizedData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={normalizedData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {selectedTickers.map((ticker, i) => (
                  <Line
                    key={ticker}
                    type="monotone"
                    dataKey={ticker}
                    stroke={COMPARISON_COLORS[i]}
                    strokeWidth={2}
                    dot={false}
                    name={ticker}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : chartData.length > 0 ? (
            <PriceLineChart data={chartData} height={400} />
          ) : (
            <p className="text-sm text-muted-foreground">No data available</p>
          )}
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      {compareMode && comparisonMetrics.length > 1 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Performance Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium">Ticker</th>
                    <th className="pb-2 font-medium text-right">Total Return</th>
                    <th className="pb-2 font-medium text-right">Period High</th>
                    <th className="pb-2 font-medium text-right">Period Low</th>
                    <th className="pb-2 font-medium text-right">Volatility (Ann.)</th>
                    <th className="pb-2 font-medium text-right">Max Drawdown</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonMetrics.map((m, i) => (
                    <tr key={m.ticker} className="border-b">
                      <td className="py-2 font-semibold" style={{ borderLeft: `3px solid ${COMPARISON_COLORS[i]}`, paddingLeft: 8 }}>
                        {m.ticker}
                      </td>
                      <td className={`text-right ${m.totalReturn >= 0 ? "text-bullish" : "text-bearish"}`}>
                        {formatPercent(m.totalReturn)}
                      </td>
                      <td className="text-right">{formatPrice(m.periodHigh)}</td>
                      <td className="text-right">{formatPrice(m.periodLow)}</td>
                      <td className="text-right">{m.volatility.toFixed(1)}%</td>
                      <td className="text-right text-bearish">-{m.maxDrawdown.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : historyData && historyData.length >= 2 && !compareMode && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Current Price</p>
              <p className="text-2xl font-bold">{formatPrice(historyData[historyData.length - 1]?.Close)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Period High</p>
              <p className="text-2xl font-bold">{formatPrice(Math.max(...historyData.map((r) => r.High)))}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Period Low</p>
              <p className="text-2xl font-bold">{formatPrice(Math.min(...historyData.map((r) => r.Low)))}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Total Return</p>
              <p className="text-2xl font-bold">
                {formatPercent(
                  ((historyData[historyData.length - 1]?.Close - historyData[0]?.Close) / historyData[0]?.Close) * 100
                )}
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
