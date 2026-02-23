"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Spinner } from "@/components/ui/loading";
import { useScreenerScan, useStrategies } from "@/lib/hooks/useScreener";
import { Search, Zap, ChevronDown } from "lucide-react";

const WATCHLISTS = [
  { value: "NIFTY50", label: "NIFTY 50" },
  { value: "NIFTY100", label: "NIFTY 100" },
  { value: "NIFTY_NEXT50", label: "NIFTY Next 50" },
  { value: "NIFTY_MIDCAP100", label: "Midcap 100" },
  { value: "NIFTY_SMALLCAP100", label: "Smallcap 100" },
  { value: "NIFTY_MIDSMALL", label: "Mid+Small (200)" },
];

const QUICK_SCANS = [
  { label: "Oversold Reversals", strategy: "oversold_reversal" },
  { label: "Strong Buy", strategy: "bullish_confluence" },
  { label: "Bearish Alerts", strategy: "bearish_confluence" },
  { label: "Breakout", strategy: "breakout" },
];

export default function ScannerPage() {
  const { data: strategies } = useStrategies();
  const scan = useScreenerScan();
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const handleScan = () => scan.restart();

  // Handle both old (array) and new ({ results, summary }) response formats
  const rawResult = scan.result;
  const results: ScreenerResult[] = Array.isArray(rawResult)
    ? rawResult
    : (rawResult as ScanResponse)?.results ?? [];
  const summary: ScanSummary | null = Array.isArray(rawResult)
    ? null
    : (rawResult as ScanResponse)?.summary ?? null;

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
                    <SelectItem key={w.value} value={w.value}>{w.label}</SelectItem>
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
              scan.restart();
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

      {scan.isComplete && rawResult && (
        <>
          {/* Summary Metrics Bar */}
          {summary && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Total Scanned</p>
                  <p className="text-2xl font-bold">{summary.total_scanned}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Matched</p>
                  <p className="text-2xl font-bold text-bullish">{summary.matched}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Avg Score</p>
                  <p className="text-2xl font-bold">{summary.avg_score}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Bias Distribution</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(summary.bias_distribution ?? {}).map(([bias, count]) => (
                      <Badge key={bias} variant={bias === "bullish" ? "bullish" : bias === "bearish" ? "bearish" : "neutral"} className="text-xs">
                        {bias}: {count as number}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Results ({results.length} stocks matched)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {results.length === 0 ? (
                <p className="text-sm text-muted-foreground">No stocks matched the criteria.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="w-8 pb-2" />
                        <th className="pb-2 font-medium">Ticker</th>
                        <th className="pb-2 font-medium text-right">Price</th>
                        <th className="pb-2 font-medium text-right">RSI</th>
                        <th className="pb-2 font-medium">MACD</th>
                        <th className="pb-2 font-medium">MA Trend</th>
                        <th className="pb-2 font-medium">Volume</th>
                        <th className="pb-2 font-medium text-right">Score</th>
                        <th className="pb-2 font-medium">Bias</th>
                        <th className="pb-2 font-medium">Matched</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((r) => (
                        <>
                          <tr
                            key={r.ticker}
                            className="border-b hover:bg-muted/50 cursor-pointer"
                            onClick={() => setExpandedRow(expandedRow === r.ticker ? null : r.ticker)}
                          >
                            <td className="py-2">
                              <ChevronDown className={`h-4 w-4 transition-transform ${expandedRow === r.ticker ? "rotate-180" : ""}`} />
                            </td>
                            <td className="py-2 font-semibold">{r.ticker}</td>
                            <td className="text-right">₹{r.current_price?.toFixed(2)}</td>
                            <td className="text-right">{r.rsi?.toFixed(1) ?? "N/A"}</td>
                            <td>{r.macd_trend ?? "N/A"}</td>
                            <td>{r.ma_trend ?? "N/A"}</td>
                            <td>{r.volume_signal ?? "N/A"}</td>
                            <td className="text-right font-semibold">{r.score}</td>
                            <td>
                              <Badge
                                variant={
                                  r.technical_bias === "bullish" ? "bullish"
                                  : r.technical_bias === "bearish" ? "bearish"
                                  : "neutral"
                                }
                              >
                                {r.technical_bias ?? "N/A"}
                              </Badge>
                            </td>
                            <td>
                              <div className="flex flex-wrap gap-1">
                                {r.matched_criteria?.slice(0, 2).map((c, i) => (
                                  <Badge key={i} variant="secondary" className="text-xs">
                                    {c}
                                  </Badge>
                                ))}
                                {(r.matched_criteria?.length ?? 0) > 2 && (
                                  <Badge variant="secondary" className="text-xs">
                                    +{(r.matched_criteria?.length ?? 0) - 2}
                                  </Badge>
                                )}
                              </div>
                            </td>
                          </tr>
                          {expandedRow === r.ticker && (
                            <tr key={`${r.ticker}-detail`} className="border-b bg-muted/30">
                              <td colSpan={10} className="p-4">
                                <div className="space-y-2">
                                  <p className="text-sm font-medium">Matched Criteria:</p>
                                  <div className="flex flex-wrap gap-2">
                                    {r.matched_criteria?.map((c, i) => (
                                      <Badge key={i} variant="secondary">{c}</Badge>
                                    ))}
                                  </div>
                                  <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4 text-sm mt-3">
                                    <div><span className="text-muted-foreground">RSI:</span> {r.rsi?.toFixed(1)}</div>
                                    <div><span className="text-muted-foreground">MACD:</span> {r.macd_trend}</div>
                                    <div><span className="text-muted-foreground">MA Trend:</span> {r.ma_trend}</div>
                                    <div><span className="text-muted-foreground">Volume:</span> {r.volume_signal}</div>
                                    <div><span className="text-muted-foreground">Score:</span> {r.score}</div>
                                    <div><span className="text-muted-foreground">Bias:</span> {r.technical_bias}</div>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

interface ScreenerResult {
  ticker: string;
  current_price: number;
  matched_criteria: string[];
  score: number;
  rsi: number;
  macd_trend: string;
  ma_trend: string;
  volume_signal: string;
  technical_bias: string;
}

interface ScanSummary {
  total_scanned: number;
  matched: number;
  avg_score: number;
  bias_distribution: Record<string, number>;
}

interface ScanResponse {
  results: ScreenerResult[];
  summary: ScanSummary;
}
