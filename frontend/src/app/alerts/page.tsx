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
import { Bell, Send, MessageSquare, TrendingUp, TrendingDown } from "lucide-react";

export default function AlertsPage() {
  const [threshold, setThreshold] = useState(1.0);
  const [tickerInput, setTickerInput] = useState("");
  const [tickers, setTickers] = useState<string[]>([]);
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

          {tickers.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tickers.map((t) => (
                <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => setTickers(tickers.filter((x) => x !== t))}>
                  {t} x
                </Badge>
              ))}
            </div>
          )}

          <Button onClick={() => { movementScan.reset(); setTimeout(() => movementScan.start(), 0); }} disabled={movementScan.isRunning || tickers.length === 0}>
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
                <CardHeader>
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
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm font-medium">{m.summary}</p>
                  {m.detailed_reason && (
                    <p className="mt-2 text-sm text-muted-foreground">{m.detailed_reason}</p>
                  )}
                  <div className="mt-2 flex gap-2">
                    <Badge variant="secondary">Confidence: {m.confidence}</Badge>
                  </div>
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
