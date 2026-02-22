"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LoadingSection } from "@/components/ui/loading";
import { useHoldings, useAddHolding, useRemoveHolding, usePortfolioAnalysis, useGrowwHoldings } from "@/lib/hooks/usePortfolio";
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

  return (
    <div className="space-y-6">
      <Header title="Portfolio Analysis" subtitle="Track your holdings against Reddit sentiment" />

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
              {isLoading ? (
                <LoadingSection />
              ) : !holdings || holdings.length === 0 ? (
                <p className="text-sm text-muted-foreground">No holdings added yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="pb-2 font-medium">Ticker</th>
                        <th className="pb-2 font-medium">Qty</th>
                        <th className="pb-2 font-medium">Avg Price</th>
                        <th className="pb-2 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.map((h) => (
                        <tr key={h.ticker} className="border-b">
                          <td className="py-2 font-semibold">{h.ticker}</td>
                          <td>{h.quantity}</td>
                          <td>{formatPrice(h.avg_price)}</td>
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
