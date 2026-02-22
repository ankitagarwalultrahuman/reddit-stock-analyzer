"use client";

import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Spinner } from "@/components/ui/loading";
import { useSwingScan } from "@/lib/hooks/useScreener";
import { formatPrice } from "@/lib/utils";
import { Zap, Target, TrendingUp } from "lucide-react";

const WATCHLISTS = ["NIFTY50", "NIFTY100", "NIFTY_NEXT50", "MIDCAP100"];

export default function SwingPage() {
  const swing = useSwingScan();
  const result = swing.result as { setups: SwingSetup[]; results_count: number } | null;

  const setupTypes = Array.from(new Set(result?.setups.map((s) => s.setup_type) ?? []));

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
                    <SelectItem key={w} value={w}>{w}</SelectItem>
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
              onClick={() => { swing.reset(); setTimeout(() => swing.start(), 0); }}
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
          <p className="text-sm text-muted-foreground">
            Scanned {result.results_count} stocks, found {result.setups.length} setups
          </p>

          {/* Tabs by Setup Type */}
          {setupTypes.length > 0 ? (
            <Tabs defaultValue={setupTypes[0]}>
              <TabsList className="flex-wrap">
                {setupTypes.map((type) => (
                  <TabsTrigger key={type} value={type}>{type}</TabsTrigger>
                ))}
              </TabsList>

              {setupTypes.map((type) => (
                <TabsContent key={type} value={type}>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {result.setups
                      .filter((s) => s.setup_type === type)
                      .map((s) => (
                        <Card key={s.ticker}>
                          <CardHeader className="pb-3">
                            <CardTitle className="flex items-center justify-between text-base">
                              <div className="flex items-center gap-2">
                                <span>{s.ticker}</span>
                                <Badge variant="secondary" className="text-xs">{s.sector}</Badge>
                              </div>
                              <span className="text-lg font-bold">{formatPrice(s.current_price)}</span>
                            </CardTitle>
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
                </TabsContent>
              ))}
            </Tabs>
          ) : (
            <Card>
              <CardContent className="py-6 text-center text-muted-foreground">
                No swing setups found. Try lowering the minimum score.
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
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
