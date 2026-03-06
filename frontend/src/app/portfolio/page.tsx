"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LoadingSection } from "@/components/ui/loading";
import { useHoldings, useAddHolding, useRemoveHolding, usePortfolioAnalysis, useGrowwHoldings, usePortfolioRisk } from "@/lib/hooks/usePortfolio";
import { formatPrice, formatPercent } from "@/lib/utils";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Plus, Trash2 } from "lucide-react";

const SENTIMENT_COLORS: Record<string, string> = {
  bullish: "#22c55e",
  bearish: "#ef4444",
  neutral: "#f59e0b",
  mixed: "#8b5cf6",
};

export default function PortfolioPage() {
  const { data: holdings, isLoading } = useHoldings();
  const { data: growwHoldings, isLoading: growwLoading } = useGrowwHoldings();
  const { data: analysis } = usePortfolioAnalysis();
  const addHolding = useAddHolding();
  const removeHolding = useRemoveHolding();
  const [riskLimits, setRiskLimits] = useState({
    max_single_position_pct: 12,
    max_sector_exposure_pct: 30,
    max_positions: 12,
    earnings_buffer_days: 7,
  });
  const { data: risk, isLoading: riskLoading } = usePortfolioRisk(riskLimits);

  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [avgPrice, setAvgPrice] = useState("");

  const handleAdd = () => {
    if (ticker && quantity && avgPrice) {
      addHolding.mutate({
        ticker: ticker.toUpperCase(),
        quantity: parseInt(quantity),
        avg_price: parseFloat(avgPrice),
      });
      setTicker("");
      setQuantity("");
      setAvgPrice("");
    }
  };

  // Build sentiment chart data from analysis
  const sentimentData = analysis?.holdings
    ? Object.entries(
        analysis.holdings.reduce<Record<string, number>>((acc, h) => {
          const s = h.sentiment || "neutral";
          acc[s] = (acc[s] || 0) + 1;
          return acc;
        }, {})
      ).map(([name, value]) => ({ name, value }))
    : [];
  const manualRows = risk?.holdings ?? [];

  return (
    <div className="space-y-6">
      <Header title="Portfolio Analysis" subtitle="Track your holdings against Reddit sentiment" />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Risk Limits</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Single Position Cap: {riskLimits.max_single_position_pct}%</label>
              <Slider
                value={[riskLimits.max_single_position_pct]}
                min={5}
                max={25}
                step={1}
                onValueChange={([v]) => setRiskLimits({ ...riskLimits, max_single_position_pct: v })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Sector Cap: {riskLimits.max_sector_exposure_pct}%</label>
              <Slider
                value={[riskLimits.max_sector_exposure_pct]}
                min={10}
                max={50}
                step={5}
                onValueChange={([v]) => setRiskLimits({ ...riskLimits, max_sector_exposure_pct: v })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Max Positions: {riskLimits.max_positions}</label>
              <Slider
                value={[riskLimits.max_positions]}
                min={4}
                max={20}
                step={1}
                onValueChange={([v]) => setRiskLimits({ ...riskLimits, max_positions: v })}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Earnings Buffer: {riskLimits.earnings_buffer_days} day(s)</label>
              <Slider
                value={[riskLimits.earnings_buffer_days]}
                min={0}
                max={14}
                step={1}
                onValueChange={([v]) => setRiskLimits({ ...riskLimits, earnings_buffer_days: v })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {risk && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Portfolio Value</p>
                <p className="text-2xl font-bold">{formatPrice(risk.summary.total_value)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Positions</p>
                <p className="text-2xl font-bold">{risk.summary.position_count}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Largest Position</p>
                <p className="text-2xl font-bold">{risk.summary.largest_position_pct.toFixed(1)}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Largest Sector</p>
                <p className="text-2xl font-bold">{risk.summary.largest_sector_pct.toFixed(1)}%</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Earnings Risk</p>
                <p className="text-2xl font-bold">{risk.summary.earnings_risk_positions}</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Sector Exposure</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {risk.sector_exposure.map((sector) => (
                    <div key={sector.sector} className="flex items-center justify-between border-b pb-2 text-sm">
                      <div>
                        <p className="font-medium">{sector.sector}</p>
                        <p className="text-xs text-muted-foreground">{formatPrice(sector.market_value)}</p>
                      </div>
                      <Badge variant={sector.is_overweight ? "bearish" : "secondary"}>{sector.exposure_pct.toFixed(1)}%</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Risk Warnings</CardTitle>
              </CardHeader>
              <CardContent>
                {risk.warnings.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No active portfolio limit breaches.</p>
                ) : (
                  <div className="space-y-2">
                    {risk.warnings.map((warning) => (
                      <Badge key={warning} variant="outline" className="mr-2 mb-2">{warning}</Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <Tabs defaultValue="manual">
        <TabsList>
          <TabsTrigger value="manual">Manual Holdings</TabsTrigger>
          <TabsTrigger value="groww">Groww Portfolio</TabsTrigger>
        </TabsList>

        {/* Manual Holdings */}
        <TabsContent value="manual" className="space-y-4">
          {/* Add Holding Form */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Ticker</label>
                  <input
                    className="flex h-10 w-32 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    placeholder="RELIANCE"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Quantity</label>
                  <input
                    className="flex h-10 w-24 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="10"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Avg Price</label>
                  <input
                    className="flex h-10 w-28 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    type="number"
                    value={avgPrice}
                    onChange={(e) => setAvgPrice(e.target.value)}
                    placeholder="2500"
                  />
                </div>
                <Button onClick={handleAdd} disabled={addHolding.isPending}>
                  <Plus className="mr-1 h-4 w-4" /> Add
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Holdings Table */}
            <Card>
            <CardHeader>
              <CardTitle className="text-base">Your Holdings</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading || riskLoading ? (
                <LoadingSection />
              ) : !holdings || holdings.length === 0 ? (
                <p className="text-sm text-muted-foreground">No holdings added yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 font-medium">Ticker</th>
                        <th className="pb-2 font-medium">Sector</th>
                        <th className="pb-2 font-medium">Qty</th>
                        <th className="pb-2 font-medium">Avg Price</th>
                        <th className="pb-2 font-medium">Current</th>
                        <th className="pb-2 font-medium">Weight</th>
                        <th className="pb-2 font-medium">Event Risk</th>
                        <th className="pb-2 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {manualRows.map((h) => (
                        <tr key={h.ticker} className="border-b">
                          <td className="py-2 font-semibold">{h.ticker}</td>
                          <td>{h.sector}</td>
                          <td>{h.quantity}</td>
                          <td>{formatPrice(h.avg_price)}</td>
                          <td>{formatPrice(h.current_price ?? h.avg_price)}</td>
                          <td>
                            <Badge variant={h.is_overweight ? "bearish" : "secondary"}>{h.weight_pct.toFixed(1)}%</Badge>
                          </td>
                          <td>
                            <Badge variant={h.has_earnings_risk ? "bearish" : "secondary"}>
                              {h.event_risk?.flag ?? "No data"}
                            </Badge>
                          </td>
                          <td>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeHolding.mutate(h.ticker)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Groww Tab */}
        <TabsContent value="groww" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Groww Holdings</CardTitle>
            </CardHeader>
            <CardContent>
              {growwLoading ? (
                <LoadingSection />
              ) : !growwHoldings || growwHoldings.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No Groww holdings found. Configure Groww API credentials in .env.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 font-medium">Symbol</th>
                        <th className="pb-2 font-medium">Qty</th>
                        <th className="pb-2 font-medium">Avg Price</th>
                        <th className="pb-2 font-medium">Current</th>
                        <th className="pb-2 font-medium">P&L</th>
                        <th className="pb-2 font-medium">P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {growwHoldings.map((h) => (
                        <tr key={h.trading_symbol} className="border-b">
                          <td className="py-2 font-semibold">{h.trading_symbol}</td>
                          <td>{h.quantity}</td>
                          <td>{formatPrice(h.average_price)}</td>
                          <td>{formatPrice(h.current_price)}</td>
                          <td className={h.pnl >= 0 ? "text-bullish" : "text-bearish"}>
                            {formatPrice(h.pnl)}
                          </td>
                          <td className={h.pnl_percent >= 0 ? "text-bullish" : "text-bearish"}>
                            {formatPercent(h.pnl_percent)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Sentiment Analysis */}
      {analysis && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sentiment Alignment</CardTitle>
            </CardHeader>
            <CardContent>
              {sentimentData.length > 0 && (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={sentimentData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" paddingAngle={4}>
                      {sentimentData.map((entry) => (
                        <Cell key={entry.name} fill={SENTIMENT_COLORS[entry.name] || "#999"} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Holdings vs Sentiment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {analysis.holdings?.map((h) => (
                  <div key={h.ticker} className="flex items-center justify-between border-b pb-2">
                    <span className="font-semibold">{h.ticker}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={h.sentiment as "bullish" | "bearish" | "neutral" | "mixed"}>
                        {h.sentiment}
                      </Badge>
                      <span className={h.change_percent >= 0 ? "text-bullish" : "text-bearish"}>
                        {formatPercent(h.change_percent)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
