"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spinner } from "@/components/ui/loading";
import DataTable, { Column } from "@/components/ui/data-table";
import { useSwingScan } from "@/lib/hooks/useScreener";
import { formatPrice, formatPercent } from "@/lib/utils";
import { Zap, Target, TrendingUp, Filter } from "lucide-react";

const WATCHLISTS = [
  { value: "NIFTY50", label: "NIFTY 50" },
  { value: "NIFTY100", label: "NIFTY 100" },
  { value: "NIFTY_NEXT50", label: "NIFTY Next 50" },
  { value: "NIFTY_MIDCAP100", label: "Midcap 100" },
  { value: "NIFTY_SMALLCAP100", label: "Smallcap 100" },
  { value: "NIFTY_MIDSMALL", label: "Mid+Small (200)" },
];

const allResultColumns: Column<ScreenerResult>[] = [
  { key: "ticker", label: "Ticker", sortable: true, render: (r) => <span className="font-semibold">{r.ticker}</span> },
  { key: "sector", label: "Sector", render: (r) => <span className="text-xs">{r.sector}</span> },
  { key: "current_price", label: "Price", sortable: true, align: "right", render: (r) => formatPrice(r.current_price) },
  { key: "rsi", label: "RSI", sortable: true, align: "right", render: (r) => r.rsi?.toFixed(1) },
  { key: "macd_signal", label: "MACD", render: (r) => r.macd_signal },
  { key: "ma_trend", label: "MA Trend", render: (r) => (
    <Badge variant={r.ma_trend === "bullish" ? "bullish" : r.ma_trend === "bearish" ? "bearish" : "neutral"}>
      {r.ma_trend}
    </Badge>
  )},
  { key: "volume_signal", label: "Volume", render: (r) => r.volume_signal },
  { key: "total_score", label: "Score", sortable: true, align: "right", render: (r) => (
    <span className="font-semibold">{r.total_score}</span>
  )},
  { key: "technical_bias", label: "Bias", render: (r) => (
    <Badge variant={r.technical_bias === "bullish" ? "bullish" : r.technical_bias === "bearish" ? "bearish" : "neutral"}>
      {r.technical_bias}
    </Badge>
  )},
  { key: "setup_count", label: "Setups", sortable: true, align: "right", render: (r) => (
    <Badge variant={r.setup_count > 0 ? "bullish" : "secondary"}>{r.setup_count}</Badge>
  )},
  { key: "relative_strength", label: "RS", sortable: true, align: "right", render: (r) => r.relative_strength?.toFixed(2) },
];

export default function SwingPage() {
  const swing = useSwingScan();
  const [setupFilter, setSetupFilter] = useState<string>("all");

  const result = swing.result as SwingResult | null;

  const setupTypes = Array.from(new Set(result?.setups?.map((s) => s.setup_type) ?? []));

  const filteredSetups = setupFilter === "all"
    ? result?.setups ?? []
    : (result?.setups ?? []).filter((s) => s.setup_type === setupFilter);

  return (
    <div className="space-y-6">
      <Header title="Swing Screener" subtitle="Find swing trading setups with entry/exit levels" />

      {/* Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Universe</label>
              <Select
                value={swing.params.watchlist}
                onValueChange={(v) => swing.setParams({ ...swing.params, watchlist: v })}
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

            <div className="space-y-1.5 w-[200px]">
              <label className="text-sm font-medium">Min Score: {swing.params.min_score}</label>
              <Slider
                value={[swing.params.min_score]}
                min={30}
                max={90}
                step={10}
                onValueChange={([v]) => swing.setParams({ ...swing.params, min_score: v })}
              />
            </div>

            <Button
              onClick={() => swing.restart()}
              disabled={swing.isRunning}
            >
              <Zap className="mr-2 h-4 w-4" />
              {swing.isRunning ? "Scanning..." : "Run Swing Screener"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {swing.isRunning && <Spinner className="py-12" />}
      {swing.isError && (
        <Card><CardContent className="py-6 text-center text-destructive">Error: {swing.error}</CardContent></Card>
      )}

      {result && (
        <>
          {/* Summary Metrics */}
          {result.summary && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Stocks Scanned</p>
                  <p className="text-2xl font-bold">{result.summary.stocks_scanned}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Setups Found</p>
                  <p className="text-2xl font-bold text-bullish">{result.summary.setups_found}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Avg Score</p>
                  <p className="text-2xl font-bold">{result.summary.avg_score}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Setup Types</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(result.summary.by_type ?? {}).map(([type, count]) => (
                      <Badge key={type} variant="secondary" className="text-xs">{type}: {count as number}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Tabs: Setups vs All Stocks */}
          <Tabs defaultValue="setups">
            <TabsList>
              <TabsTrigger value="setups">Setups ({result.setups?.length ?? 0})</TabsTrigger>
              <TabsTrigger value="all">All Screened Stocks ({result.all_results?.length ?? 0})</TabsTrigger>
            </TabsList>

            <TabsContent value="setups">
              {/* Setup Type Filter */}
              {setupTypes.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-4">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <Button
                    variant={setupFilter === "all" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSetupFilter("all")}
                  >
                    All ({result.setups?.length ?? 0})
                  </Button>
                  {setupTypes.map((type) => (
                    <Button
                      key={type}
                      variant={setupFilter === type ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSetupFilter(type)}
                    >
                      {type} ({(result.setups ?? []).filter((s) => s.setup_type === type).length})
                    </Button>
                  ))}
                </div>
              )}

              {filteredSetups.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredSetups.map((s, i) => (
                    <Card key={`${s.ticker}-${i}`}>
                      <CardHeader className="pb-3">
                        <CardTitle className="flex items-center justify-between text-base">
                          <div className="flex items-center gap-2">
                            <span>{s.ticker}</span>
                            <Badge variant="secondary" className="text-xs">{s.sector}</Badge>
                          </div>
                          <span className="text-lg font-bold">{formatPrice(s.current_price)}</span>
                        </CardTitle>
                        <Badge variant={s.setup_type.includes("Breakdown") ? "bearish" : "bullish"} className="w-fit text-xs">
                          {s.setup_type}
                        </Badge>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-xs text-muted-foreground">Entry Zone</p>
                            <p className="font-medium">
                              {formatPrice(s.entry_zone?.[0])} - {formatPrice(s.entry_zone?.[1])}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Stop Loss</p>
                            <p className="font-medium text-bearish">{formatPrice(s.stop_loss)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Target 1</p>
                            <p className="font-medium text-bullish">{formatPrice(s.target_1)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Target 2</p>
                            <p className="font-medium text-bullish">{formatPrice(s.target_2)}</p>
                          </div>
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            <Target className="h-3.5 w-3.5" />
                            <span className="text-xs">R:R {s.risk_reward?.toFixed(1)}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <TrendingUp className="h-3.5 w-3.5" />
                            <span className="text-xs">RS {s.relative_strength?.toFixed(2)}</span>
                          </div>
                          <Badge variant={s.confidence_score >= 7 ? "bullish" : s.confidence_score >= 5 ? "neutral" : "bearish"}>
                            {s.confidence_score}/10
                          </Badge>
                        </div>

                        {s.signals && s.signals.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {s.signals.slice(0, 4).map((sig, i) => (
                              <Badge key={i} variant="secondary" className="text-xs">{sig}</Badge>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <Card>
                  <CardContent className="py-6 text-center text-muted-foreground">
                    No swing setups found. Try lowering the minimum score.
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="all">
              <DataTable
                data={(result.all_results ?? []) as ScreenerResult[]}
                columns={allResultColumns}
                defaultSortKey="total_score"
                expandable={(row) => (
                  <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5 text-sm">
                    <div><span className="text-muted-foreground">Week Change:</span> <span className={row.week_change >= 0 ? "text-bullish" : "text-bearish"}>{formatPercent(row.week_change)}</span></div>
                    <div><span className="text-muted-foreground">Support:</span> {formatPrice(row.support)}</div>
                    <div><span className="text-muted-foreground">Resistance:</span> {formatPrice(row.resistance)}</div>
                    <div><span className="text-muted-foreground">Tech Score:</span> {row.technical_score}</div>
                    <div><span className="text-muted-foreground">52W High:</span> {formatPrice(row.week_52_high)}</div>
                    <div><span className="text-muted-foreground">52W Low:</span> {formatPrice(row.week_52_low)}</div>
                    <div><span className="text-muted-foreground">From 52W High:</span> {row.pct_from_52w_high?.toFixed(1)}%</div>
                    <div><span className="text-muted-foreground">Near 52W High:</span> {row.near_52w_high ? "Yes" : "No"}</div>
                  </div>
                )}
              />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

interface SwingResult {
  results_count: number;
  setups: SwingSetup[];
  all_results: ScreenerResult[];
  summary: {
    stocks_scanned: number;
    setups_found: number;
    avg_score: number;
    by_type: Record<string, number>;
    bias_distribution: Record<string, number>;
  };
}

interface SwingSetup {
  ticker: string;
  sector: string;
  setup_type: string;
  current_price: number;
  entry_zone: [number, number];
  stop_loss: number;
  target_1: number;
  target_2: number;
  risk_reward: number;
  confidence_score: number;
  signals: string[];
  relative_strength: number;
}

interface ScreenerResult {
  ticker: string;
  sector: string;
  current_price: number;
  week_change: number;
  rsi: number;
  macd_signal: string;
  ma_trend: string;
  volume_signal: string;
  technical_bias: string;
  technical_score: number;
  relative_strength: number;
  support: number;
  resistance: number;
  total_score: number;
  setup_count: number;
  week_52_high: number;
  week_52_low: number;
  pct_from_52w_high: number;
  near_52w_high: boolean;
  [key: string]: unknown;
}
