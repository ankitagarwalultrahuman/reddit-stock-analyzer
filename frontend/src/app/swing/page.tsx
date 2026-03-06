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
import { useSwingScan, useWatchlists } from "@/lib/hooks/useScreener";
import { formatPrice, formatPercent } from "@/lib/utils";
import { Zap, Target, TrendingUp, Filter } from "lucide-react";

const FALLBACK_WATCHLISTS = [
  { name: "NIFTY50", label: "NIFTY 50" },
  { name: "NIFTY100", label: "NIFTY 100" },
  { name: "NIFTY200", label: "NIFTY 200" },
  { name: "NSE_LIQUID_SWING", label: "NSE Liquid Swing" },
  { name: "NSE_EXPANDED_SWING", label: "NSE Expanded Swing" },
];

function portfolioActionVariant(action?: string): "bullish" | "bearish" | "neutral" | "secondary" {
  if (action === "allow") return "bullish";
  if (action === "avoid") return "bearish";
  if (action === "trim") return "neutral";
  return "secondary";
}

function eventRiskVariant(level?: string): "bullish" | "bearish" | "neutral" | "secondary" {
  if (level === "critical" || level === "high") return "bearish";
  if (level === "elevated" || level === "watch") return "neutral";
  if (level === "none" || level === "monitor") return "bullish";
  return "secondary";
}

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
  { key: "liquidity_tier", label: "Liquidity", render: (r) => (
    <Badge variant={r.liquidity_tier === "illiquid" ? "bearish" : r.liquidity_tier === "tradable" ? "neutral" : "bullish"}>
      {r.liquidity_tier}
    </Badge>
  )},
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
  { key: "event_risk_level", label: "Event Risk", render: (r) => (
    <Badge variant={eventRiskVariant(r.event_risk_level)}>{r.event_risk_level ?? "unknown"}</Badge>
  )},
  { key: "portfolio_action", label: "Portfolio Fit", render: (r) => (
    <Badge variant={portfolioActionVariant(r.portfolio_action)}>{r.portfolio_action ?? "allow"}</Badge>
  )},
];

export default function SwingPage() {
  const swing = useSwingScan();
  const { data: watchlists } = useWatchlists();
  const [setupFilter, setSetupFilter] = useState<string>("all");
  const watchlistOptions = watchlists?.filter((item) => item.is_preset) ?? FALLBACK_WATCHLISTS;

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
          <div className="grid gap-4 lg:grid-cols-3 xl:grid-cols-6">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Universe</label>
              <Select
                value={swing.params.watchlist}
                onValueChange={(v) => swing.setParams({ ...swing.params, watchlist: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {watchlistOptions.map((w) => (
                    <SelectItem key={w.name} value={w.name}>{w.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Min Score: {swing.params.min_score}</label>
              <Slider
                value={[swing.params.min_score]}
                min={30}
                max={90}
                step={10}
                onValueChange={([v]) => swing.setParams({ ...swing.params, min_score: v })}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Single Position Cap: {swing.params.max_single_position_pct}%</label>
              <Slider
                value={[swing.params.max_single_position_pct]}
                min={5}
                max={25}
                step={1}
                onValueChange={([v]) => swing.setParams({ ...swing.params, max_single_position_pct: v })}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Sector Cap: {swing.params.max_sector_exposure_pct}%</label>
              <Slider
                value={[swing.params.max_sector_exposure_pct]}
                min={10}
                max={50}
                step={5}
                onValueChange={([v]) => swing.setParams({ ...swing.params, max_sector_exposure_pct: v })}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Earnings Buffer: {swing.params.earnings_buffer_days} day(s)</label>
              <Slider
                value={[swing.params.earnings_buffer_days]}
                min={0}
                max={14}
                step={1}
                onValueChange={([v]) => swing.setParams({ ...swing.params, earnings_buffer_days: v })}
              />
            </div>

            <div className="flex flex-col justify-between gap-3 rounded-lg border border-border/60 p-3">
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  checked={swing.params.include_portfolio_context}
                  onChange={(e) => swing.setParams({ ...swing.params, include_portfolio_context: e.target.checked })}
                />
                Portfolio-aware ranking
              </label>
              <p className="text-xs text-muted-foreground">
                Penalize setups that breach name caps, sector caps, or have near-term results risk.
              </p>
              <Button
                onClick={() => swing.restart()}
                disabled={swing.isRunning}
              >
                <Zap className="mr-2 h-4 w-4" />
                {swing.isRunning ? "Scanning..." : "Run Swing Screener"}
              </Button>
            </div>

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
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Regimes</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(result.summary.by_regime ?? {}).map(([regime, count]) => (
                      <Badge key={regime} variant="secondary" className="text-xs">{regime}: {count as number}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Portfolio Actions</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(result.summary.portfolio_actions ?? {}).map(([action, count]) => (
                      <Badge key={action} variant={portfolioActionVariant(action)} className="text-xs">{action}: {count as number}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Event Risk</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(result.summary.event_risk_distribution ?? {}).filter(([, count]) => Number(count) > 0).map(([level, count]) => (
                      <Badge key={level} variant={eventRiskVariant(level)} className="text-xs">{level}: {count as number}</Badge>
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
                        <Badge variant="secondary" className="w-fit text-xs">
                          {s.regime}
                        </Badge>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant={portfolioActionVariant(s.portfolio_action)} className="w-fit text-xs">
                            {s.portfolio_action ?? "allow"}
                          </Badge>
                          <Badge variant={eventRiskVariant(s.event_risk_level)} className="w-fit text-xs">
                            {s.event_risk_level ?? "unknown"}
                          </Badge>
                        </div>
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

                        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                          <div>Holding Window: {s.holding_window}</div>
                          <div>Stop Distance: {s.stop_distance_pct?.toFixed(1)}%</div>
                          <div>Setup Size: {s.capital_allocation_pct?.toFixed(1)}%</div>
                          <div>RS vs NIFTY: {s.relative_strength?.toFixed(2)}%</div>
                          <div>Recommended Size: {s.recommended_allocation_pct?.toFixed(1)}%</div>
                          <div>Sector Exposure: {s.sector_exposure_pct?.toFixed(1)}%</div>
                          <div>Current Position: {s.current_position_pct?.toFixed(1)}%</div>
                          <div>Event Date: {s.event_date ?? "N/A"}</div>
                        </div>

                        {s.portfolio_flags && s.portfolio_flags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {s.portfolio_flags.map((flag, i) => (
                              <Badge key={`${flag}-${i}`} variant="outline" className="text-xs">{flag}</Badge>
                            ))}
                          </div>
                        )}

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
                    <div><span className="text-muted-foreground">Primary Setup:</span> {row.primary_setup || "None"}</div>
                    <div><span className="text-muted-foreground">Liquidity:</span> {row.liquidity_tier}</div>
                    <div><span className="text-muted-foreground">ADV:</span> {row.avg_traded_value_cr ? `₹${row.avg_traded_value_cr} Cr` : "N/A"}</div>
                    <div><span className="text-muted-foreground">52W High:</span> {formatPrice(row.week_52_high)}</div>
                    <div><span className="text-muted-foreground">52W Low:</span> {formatPrice(row.week_52_low)}</div>
                    <div><span className="text-muted-foreground">From 52W High:</span> {row.pct_from_52w_high?.toFixed(1)}%</div>
                    <div><span className="text-muted-foreground">Near 52W High:</span> {row.near_52w_high ? "Yes" : "No"}</div>
                    <div><span className="text-muted-foreground">Portfolio Fit:</span> {row.portfolio_action}</div>
                    <div><span className="text-muted-foreground">Recommended Size:</span> {row.recommended_allocation_pct?.toFixed(1)}%</div>
                    <div><span className="text-muted-foreground">Event Risk:</span> {row.event_risk_level}</div>
                    <div><span className="text-muted-foreground">Event Date:</span> {row.event_date ?? "N/A"}</div>
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
    by_regime?: Record<string, number>;
    bias_distribution: Record<string, number>;
    liquidity_distribution?: Record<string, number>;
    portfolio_actions?: Record<string, number>;
    event_risk_distribution?: Record<string, number>;
    risk_limits?: {
      max_single_position_pct: number;
      max_sector_exposure_pct: number;
      max_positions: number;
      earnings_buffer_days: number;
    };
  };
}

interface SwingSetup {
  ticker: string;
  sector: string;
  setup_type: string;
  regime: string;
  current_price: number;
  entry_zone: [number, number];
  stop_loss: number;
  target_1: number;
  target_2: number;
  risk_reward: number;
  confidence_score: number;
  signals: string[];
  relative_strength: number;
  holding_window: string;
  stop_distance_pct: number;
  capital_allocation_pct: number;
  recommended_allocation_pct?: number;
  portfolio_action?: string;
  portfolio_flags?: string[];
  sector_exposure_pct?: number;
  current_position_pct?: number;
  event_risk_level?: string;
  event_date?: string | null;
  days_to_event?: number | null;
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
  primary_setup?: string;
  avg_traded_value_cr?: number;
  liquidity_tier: string;
  week_52_high: number;
  week_52_low: number;
  pct_from_52w_high: number;
  near_52w_high: boolean;
  event_risk_level?: string;
  event_date?: string | null;
  days_to_event?: number | null;
  portfolio_action?: string;
  recommended_allocation_pct?: number;
  portfolio_flags?: string[];
  sector_exposure_pct?: number;
  current_position_pct?: number;
  [key: string]: unknown;
}
