"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LoadingSection } from "@/components/ui/loading";
import PriceLineChart from "@/components/charts/PriceLineChart";
import { useStockHistory } from "@/lib/hooks/useStocks";
import { useHoldings } from "@/lib/hooks/usePortfolio";
import { useStockMentions, useReportDates } from "@/lib/hooks/useReport";
import { formatPrice, formatPercent } from "@/lib/utils";

const POPULAR_STOCKS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"];

export default function HistoryPage() {
  const [selectedTickers, setSelectedTickers] = useState<string[]>(["RELIANCE"]);
  const [days, setDays] = useState(30);
  const [customTicker, setCustomTicker] = useState("");
  const { data: holdings } = useHoldings();
  const { data: dates } = useReportDates();
  const { data: stocks } = useStockMentions(dates?.[0] ?? null);

  const { data: historyData, isLoading } = useStockHistory(
    selectedTickers[0] ?? null,
    days
  );

  const chartData = historyData?.map((r) => ({
    date: (r.Date || r.index || "").slice(5),
    close: r.Close,
  })) ?? [];

  return (
    <div className="space-y-6">
      <Header title="Historic Performance" subtitle="Track stock price history and performance metrics" />

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
                onClick={() => setSelectedTickers([t])}
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
                onClick={() => setSelectedTickers([h.ticker])}
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
                onClick={() => setSelectedTickers([s.ticker])}
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
                  setSelectedTickers([customTicker.toUpperCase()]);
                  setCustomTicker("");
                }
              }}
              placeholder="Enter ticker"
            />
            <Button
              size="sm"
              onClick={() => {
                if (customTicker) {
                  setSelectedTickers([customTicker.toUpperCase()]);
                  setCustomTicker("");
                }
              }}
            >
              Go
            </Button>
          </div>
        </TabsContent>
      </Tabs>

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
            {selectedTickers.join(", ")} - {days} Day Chart
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingSection />
          ) : chartData.length > 0 ? (
            <PriceLineChart data={chartData} height={400} />
          ) : (
            <p className="text-sm text-muted-foreground">No data available</p>
          )}
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      {historyData && historyData.length >= 2 && (
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
