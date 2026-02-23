"use client";

import { useState, useCallback } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Spinner } from "@/components/ui/loading";
import { useAsyncTask } from "@/lib/hooks/useScreener";
import { useHoldings } from "@/lib/hooks/usePortfolio";
import { api } from "@/lib/api";
import { Bell, Send, MessageSquare, TrendingUp, TrendingDown, ChevronDown } from "lucide-react";

const PRESET_WATCHLISTS: { label: string; tickers: string[] }[] = [
  { label: "NIFTY50 Top 10", tickers: ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "LT"] },
  { label: "Midcap Leaders", tickers: ["PERSISTENT", "COFORGE", "MPHASIS", "POLYCAB", "PIIND", "ASTRAL", "ATUL", "DEEPAKNTR"] },
  { label: "Bank Pack", tickers: ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "BANKBARODA", "PNB"] },
  { label: "IT Pack", tickers: ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "COFORGE"] },
];

export default function AlertsPage() {
  const [threshold, setThreshold] = useState(1.0);
  const [tickerInput, setTickerInput] = useState("");
  const [tickers, setTickers] = useState<string[]>([]);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const { data: holdings } = useHoldings();

  const movementScan = useAsyncTask(
    useCallback(() => api.startMovementScan(tickers, threshold), [tickers, threshold]),
    api.getMovementResult
  );

  const addTicker = () => {
    const t = tickerInput.trim().toUpperCase();
    if (t && !tickers.includes(t)) {
      setTickers([...tickers, t]);
      setTickerInput("");
    }
  };

  const loadPortfolioTickers = () => {
    if (holdings) {
      const pts = holdings.map((h) => h.ticker);
      setTickers(Array.from(new Set([...tickers, ...pts])));
    }
  };

  const loadPreset = (preset: typeof PRESET_WATCHLISTS[number]) => {
    setTickers(Array.from(new Set([...tickers, ...preset.tickers])));
  };

  return (
    <div className="space-y-6">
      <Header title="Movement Alerts" subtitle="Detect significant price movements and get AI analysis" />

      {/* Controls */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="space-y-1.5 max-w-sm">
            <label className="text-sm font-medium">Movement Threshold: {threshold}%</label>
            <Slider
              value={[threshold]}
              min={0.5}
              max={5}
              step={0.5}
              onValueChange={([v]) => setThreshold(v)}
            />
          </div>

          <div className="flex items-end gap-2">
            <div className="space-y-1.5 flex-1 max-w-sm">
              <label className="text-sm font-medium">Add Tickers</label>
              <input
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addTicker()}
                placeholder="e.g. RELIANCE"
              />
            </div>
            <Button variant="outline" onClick={addTicker}>Add</Button>
            <Button variant="outline" onClick={loadPortfolioTickers}>
              Load Portfolio
            </Button>
          </div>

          {/* Preset Watchlists */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Quick Load Presets</label>
            <div className="flex flex-wrap gap-2">
              {PRESET_WATCHLISTS.map((p) => (
                <Button
                  key={p.label}
                  variant="outline"
                  size="sm"
                  onClick={() => loadPreset(p)}
                >
                  {p.label}
                </Button>
              ))}
            </div>
          </div>

          {tickers.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tickers.map((t) => (
                <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => setTickers(tickers.filter((x) => x !== t))}>
                  {t} x
                </Badge>
              ))}
              <Button variant="ghost" size="sm" className="text-xs" onClick={() => setTickers([])}>
                Clear All
              </Button>
            </div>
          )}

          <Button onClick={() => movementScan.restart()} disabled={movementScan.isRunning || tickers.length === 0}>
            <Bell className="mr-2 h-4 w-4" />
            {movementScan.isRunning ? "Scanning..." : "Detect Movements"}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {movementScan.isRunning && <Spinner className="py-12" />}

      {movementScan.isComplete && movementScan.result && (
        <div className="space-y-4">
          {(movementScan.result as MovementResult[]).length === 0 ? (
            <Card>
              <CardContent className="py-6 text-center text-muted-foreground">
                No significant movements detected above {threshold}% threshold.
              </CardContent>
            </Card>
          ) : (
            (movementScan.result as MovementResult[]).map((m, i) => (
              <Card key={i}>
                <CardHeader
                  className="cursor-pointer"
                  onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                >
                  <CardTitle className="flex items-center gap-2 text-base">
                    {m.direction === "up" ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                    {m.ticker}
                    <Badge variant={m.direction === "up" ? "bullish" : "bearish"}>
                      {m.change_percent > 0 ? "+" : ""}{m.change_percent?.toFixed(2)}%
                    </Badge>
                    <Badge variant="secondary">Confidence: {m.confidence}</Badge>
                    <ChevronDown className={`ml-auto h-4 w-4 transition-transform ${expandedIdx === i ? "rotate-180" : ""}`} />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm font-medium">{m.summary}</p>
                  {expandedIdx === i && m.detailed_reason && (
                    <div className="mt-3 p-3 bg-muted/30 rounded-md">
                      <p className="text-sm font-medium mb-1">Detailed Analysis:</p>
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">{m.detailed_reason}</p>
                      {m.sources && m.sources.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-muted-foreground">Sources:</p>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {m.sources.map((s, j) => (
                              <Badge key={j} variant="secondary" className="text-xs">{s}</Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Test Notifications */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Send className="h-4 w-4" />
              Telegram Test
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={() => api.testTelegram("Test alert from Brodus Analytics")}
            >
              Send Test Message
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquare className="h-4 w-4" />
              SMS Test
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={() => api.testSms("Test SMS from Brodus Analytics")}
            >
              Send Test SMS
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface MovementResult {
  ticker: string;
  change_percent: number;
  direction: string;
  summary: string;
  detailed_reason: string;
  confidence: string;
  sources: string[];
}
