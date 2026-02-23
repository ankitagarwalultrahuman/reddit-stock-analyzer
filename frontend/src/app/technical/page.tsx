"use client";

import { useState, useEffect } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/loading";
import TechnicalChart from "@/components/charts/TechnicalChart";
import { useStockTechnicals } from "@/lib/hooks/useStocks";
import { useStockMentions, useReportDates, useConfluenceSignals } from "@/lib/hooks/useReport";
import { formatPrice } from "@/lib/utils";

export default function TechnicalPage() {
  const { data: dates } = useReportDates();
  const { data: stocks } = useStockMentions(dates?.[0] ?? null);
  const { data: confluence } = useConfluenceSignals(dates?.[0] ?? undefined);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const { data: techData, isLoading } = useStockTechnicals(selectedTicker, 60);

  useEffect(() => {
    if (stocks && stocks.length > 0 && !selectedTicker) {
      setSelectedTicker(stocks[0].ticker);
    }
  }, [stocks, selectedTicker]);

  const t = techData?.technicals;
  const history = techData?.history ?? [];

  const chartData = history.map((r) => ({
    time: (r.Date || r.index || "").slice(0, 10),
    open: r.Open,
    high: r.High,
    low: r.Low,
    close: r.Close,
    volume: r.Volume,
  }));

  const indicators = t
    ? [
        { label: "RSI", value: t.rsi?.toFixed(1), signal: t.rsi_signal, color: t.rsi_signal === "oversold" ? "bullish" : t.rsi_signal === "overbought" ? "bearish" : "neutral" },
        { label: "MACD Trend", value: t.macd_trend, signal: t.macd_trend, color: t.macd_trend?.includes("bullish") ? "bullish" : t.macd_trend?.includes("bearish") ? "bearish" : "neutral" },
        { label: "MA Trend", value: t.ma_trend, signal: t.ma_trend, color: t.ma_trend === "bullish" ? "bullish" : t.ma_trend === "bearish" ? "bearish" : "neutral" },
        { label: "Volume", value: `${t.volume_ratio?.toFixed(1)}x`, signal: t.volume_signal, color: t.volume_signal === "high" ? "bullish" : "neutral" },
        { label: "ATR", value: `${t.atr_percent?.toFixed(1)}%`, signal: t.volatility_level, color: "neutral" },
        { label: "ADX", value: t.adx?.toFixed(1), signal: t.adx_signal, color: t.adx_signal === "strong_trend" ? "bullish" : "neutral" },
        { label: "Stoch RSI", value: t.stoch_rsi_k?.toFixed(1), signal: t.stoch_rsi_signal, color: t.stoch_rsi_signal?.includes("bullish") ? "bullish" : t.stoch_rsi_signal?.includes("bearish") ? "bearish" : "neutral" },
        { label: "BB Position", value: t.bb_position, signal: t.bb_position, color: t.bb_position?.includes("lower") ? "bullish" : t.bb_position?.includes("upper") ? "bearish" : "neutral" },
        { label: "52W High", value: formatPrice(t.week_52_high), signal: `${t.pct_from_52w_high?.toFixed(1)}% from high`, color: "neutral" },
        { label: "Tech Score", value: `${t.technical_score}/100`, signal: t.technical_bias, color: t.technical_bias === "bullish" ? "bullish" : t.technical_bias === "bearish" ? "bearish" : "neutral" },
        { label: "Divergence", value: t.divergence ?? "None", signal: t.divergence_strength, color: t.divergence === "bullish" ? "bullish" : t.divergence === "bearish" ? "bearish" : "neutral" },
        { label: "BB Width", value: t.bb_width?.toFixed(3), signal: t.volatility_level, color: "neutral" },
      ]
    : [];

  return (
    <div className="space-y-6">
      <Header title="Technical Analysis" subtitle="In-depth technical indicators and charts" />

      {/* Stock Selector */}
      <div className="flex flex-wrap gap-2">
        {stocks?.slice(0, 12).map((s) => (
          <Button
            key={s.ticker}
            variant={selectedTicker === s.ticker ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedTicker(s.ticker)}
          >
            {s.ticker}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <Spinner className="py-12" />
      ) : techData?.success ? (
        <>
          {/* Candlestick Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                {selectedTicker}
                <span className="text-lg font-bold">{formatPrice(techData.current_price)}</span>
                {t && (
                  <Badge variant={t.technical_bias === "bullish" ? "bullish" : t.technical_bias === "bearish" ? "bearish" : "neutral"}>
                    {t.technical_bias}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <TechnicalChart data={chartData} height={350} showRSI showMACD />
            </CardContent>
          </Card>

          {/* Indicator Grid */}
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {indicators.map((ind) => (
              <Card key={ind.label}>
                <CardContent className="py-4">
                  <p className="text-xs text-muted-foreground">{ind.label}</p>
                  <p className="text-lg font-bold">{ind.value ?? "N/A"}</p>
                  {ind.signal && (
                    <Badge variant={ind.color as "bullish" | "bearish" | "neutral"} className="mt-1">
                      {ind.signal}
                    </Badge>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Confluence Signals */}
          {confluence && confluence.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Confluence Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 font-medium">Ticker</th>
                        <th className="pb-2 font-medium">Sentiment</th>
                        <th className="pb-2 font-medium">Score</th>
                        <th className="pb-2 font-medium">Signals</th>
                      </tr>
                    </thead>
                    <tbody>
                      {confluence.map((s) => (
                        <tr key={s.ticker} className="border-b">
                          <td className="py-2 font-semibold">{s.ticker}</td>
                          <td><Badge variant={s.sentiment as "bullish" | "bearish" | "neutral" | "mixed"}>{s.sentiment}</Badge></td>
                          <td>{s.confluence_score}</td>
                          <td className="text-xs">{s.aligned_signals?.join(", ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="py-6 text-center text-muted-foreground">
            {techData?.error || "Select a stock to view technical analysis"}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
