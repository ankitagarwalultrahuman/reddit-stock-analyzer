"use client";

import { useCallback } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Spinner } from "@/components/ui/loading";
import { useScreenerScan, useStrategies } from "@/lib/hooks/useScreener";
import { Search, Zap } from "lucide-react";

const WATCHLISTS = ["NIFTY50", "NIFTY100", "NIFTY_NEXT50", "MIDCAP100"];

const QUICK_SCANS = [
  { label: "Oversold Reversals", strategy: "oversold_reversal" },
  { label: "Strong Buy", strategy: "bullish_confluence" },
  { label: "Bearish Alerts", strategy: "bearish_confluence" },
  { label: "Breakout", strategy: "breakout" },
];

export default function ScannerPage() {
  const { data: strategies } = useStrategies();
  const scan = useScreenerScan();

  const handleScan = useCallback(() => {
    scan.reset();
    setTimeout(() => scan.start(), 0);
  }, [scan]);

  return (
    <div className="space-y-6">
      <Header title="Watchlist Scanner" subtitle="Scan stocks using technical strategies" />

      {/* Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Watchlist</label>
              <Select
                value={scan.params.watchlist}
                onValueChange={(v) => scan.setParams({ ...scan.params, watchlist: v })}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WATCHLISTS.map((w) => (
                    <SelectItem key={w} value={w}>{w}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Strategy</label>
              <Select
                value={scan.params.strategy}
                onValueChange={(v) => scan.setParams({ ...scan.params, strategy: v })}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategies && Object.entries(strategies).map(([key, s]) => (
                    <SelectItem key={key} value={key}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5 w-[200px]">
              <label className="text-sm font-medium">Min Matches: {scan.params.min_matches}</label>
              <Slider
                value={[scan.params.min_matches]}
                min={1}
                max={5}
                step={1}
                onValueChange={([v]) => scan.setParams({ ...scan.params, min_matches: v })}
              />
            </div>

            <Button onClick={handleScan} disabled={scan.isRunning}>
              <Search className="mr-2 h-4 w-4" />
              {scan.isRunning ? "Scanning..." : "Run Scan"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Scan Buttons */}
      <div className="flex flex-wrap gap-2">
        {QUICK_SCANS.map((q) => (
          <Button
            key={q.strategy}
            variant="outline"
            size="sm"
            onClick={() => {
              scan.setParams({ ...scan.params, strategy: q.strategy });
              scan.reset();
              setTimeout(() => scan.start(), 0);
            }}
            disabled={scan.isRunning}
          >
            <Zap className="mr-1.5 h-3 w-3" />
            {q.label}
          </Button>
        ))}
      </div>

      {/* Results */}
      {scan.isRunning && <Spinner className="py-12" />}

      {scan.isError && (
        <Card>
          <CardContent className="py-6 text-center text-destructive">
            Scan failed: {scan.error}
          </CardContent>
        </Card>
      )}

      {scan.isComplete && scan.result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Results ({(scan.result as ScreenerResult[]).length} stocks matched)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(scan.result as ScreenerResult[]).length === 0 ? (
              <p className="text-sm text-muted-foreground">No stocks matched the criteria.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 font-medium">Ticker</th>
                      <th className="pb-2 font-medium">Price</th>
                      <th className="pb-2 font-medium">RSI</th>
                      <th className="pb-2 font-medium">MACD</th>
                      <th className="pb-2 font-medium">MA Trend</th>
                      <th className="pb-2 font-medium">Volume</th>
                      <th className="pb-2 font-medium">Score</th>
                      <th className="pb-2 font-medium">Bias</th>
                      <th className="pb-2 font-medium">Matched</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(scan.result as ScreenerResult[]).map((r) => (
                      <tr key={r.ticker} className="border-b hover:bg-muted/50">
                        <td className="py-2 font-semibold">{r.ticker}</td>
                        <td>₹{r.current_price?.toFixed(2)}</td>
                        <td>{r.rsi?.toFixed(1) ?? "N/A"}</td>
                        <td>{r.macd_trend ?? "N/A"}</td>
                        <td>{r.ma_trend ?? "N/A"}</td>
                        <td>{r.volume_signal ?? "N/A"}</td>
                        <td className="font-semibold">{r.score}</td>
                        <td>
                          <Badge
                            variant={
                              r.technical_bias === "bullish"
                                ? "bullish"
                                : r.technical_bias === "bearish"
                                ? "bearish"
                                : "neutral"
                            }
                          >
                            {r.technical_bias ?? "N/A"}
                          </Badge>
                        </td>
                        <td>
                          <div className="flex flex-wrap gap-1">
                            {r.matched_criteria?.map((c, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">
                                {c}
                              </Badge>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
