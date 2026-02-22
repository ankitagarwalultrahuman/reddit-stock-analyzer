"use client";

import { useState, useEffect } from "react";
import Header from "@/components/layout/Header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { LoadingCards, LoadingSection } from "@/components/ui/loading";
import TodaysActions from "@/components/dashboard/TodaysActions";
import NewsHighlights from "@/components/dashboard/NewsHighlights";
import WeeklySummary from "@/components/dashboard/WeeklySummary";
import StockMentionsBar from "@/components/charts/StockMentionsBar";
import SentimentDonut from "@/components/charts/SentimentDonut";
import {
  useReportDates,
  useActions,
  useStockMentions,
  useInsights,
  useSections,
  useSentiment,
  useSessions,
  useComparison,
  useConfluenceSignals,
  useNewsHighlights,
} from "@/lib/hooks/useReport";

export default function DashboardPage() {
  const { data: dates } = useReportDates();
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  useEffect(() => {
    if (dates && dates.length > 0 && !selectedDate) {
      setSelectedDate(dates[0]);
    }
  }, [dates, selectedDate]);

  const { data: actions, isLoading: actionsLoading } = useActions(selectedDate);
  const { data: stocks, isLoading: stocksLoading } = useStockMentions(selectedDate);
  const { data: insights } = useInsights(selectedDate);
  const { data: sections } = useSections(selectedDate);
  const { data: sentiment, isLoading: sentimentLoading } = useSentiment(selectedDate);
  const { data: sessions } = useSessions(selectedDate);
  const { data: comparison } = useComparison(selectedDate);
  const { data: confluence } = useConfluenceSignals(selectedDate ?? undefined);
  const { data: newsData } = useNewsHighlights();

  return (
    <div className="space-y-6">
      <Header title="Brodus Analytics" subtitle="Indian Stock Market Intelligence from Reddit" />

      {/* Date Selector */}
      <div className="flex items-center gap-4">
        <Select value={selectedDate ?? ""} onValueChange={setSelectedDate}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Select date" />
          </SelectTrigger>
          <SelectContent>
            {(dates ?? []).map((d) => (
              <SelectItem key={d} value={d}>
                {new Date(d + "T00:00:00").toLocaleDateString("en-IN", {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {sessions?.has_both && (
          <Badge variant="secondary">AM + PM available</Badge>
        )}
      </div>

      {/* Session Tabs */}
      {sessions?.has_both && (
        <Tabs defaultValue="latest">
          <TabsList>
            <TabsTrigger value="latest">Latest</TabsTrigger>
            <TabsTrigger value="am">AM Session</TabsTrigger>
            <TabsTrigger value="pm">PM Session</TabsTrigger>
            {comparison?.has_comparison && (
              <TabsTrigger value="comparison">AM vs PM</TabsTrigger>
            )}
          </TabsList>
          {comparison?.has_comparison && (
            <TabsContent value="comparison">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">AM vs PM Comparison</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm">
                    {comparison.content}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          )}
        </Tabs>
      )}

      {/* Today's Actions */}
      {actionsLoading ? (
        <LoadingCards />
      ) : actions ? (
        <>
          <TodaysActions
            watchList={actions.watch_list}
            considerList={actions.consider_list}
            avoidList={actions.avoid_list}
            riskAlerts={actions.risk_alerts}
            marketMood={actions.market_mood}
          />
          {actions.focus_summary && (
            <Card>
              <CardContent className="py-4">
                <p className="text-sm font-medium text-muted-foreground">
                  {actions.focus_summary}
                </p>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Most Discussed Stocks</CardTitle>
          </CardHeader>
          <CardContent>
            {stocksLoading ? (
              <LoadingSection />
            ) : stocks && stocks.length > 0 ? (
              <StockMentionsBar data={stocks} />
            ) : (
              <p className="text-sm text-muted-foreground">No stock mentions available</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sentiment Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {sentimentLoading ? (
              <LoadingSection />
            ) : sentiment ? (
              <SentimentDonut data={sentiment} />
            ) : (
              <p className="text-sm text-muted-foreground">No sentiment data</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Report Metrics */}
      {insights && insights.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Stocks Analyzed</p>
              <p className="text-2xl font-bold">{stocks?.length ?? 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Key Insights</p>
              <p className="text-2xl font-bold">{insights.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Confluence Signals</p>
              <p className="text-2xl font-bold">{confluence?.length ?? 0}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Bullish / Bearish</p>
              <p className="text-2xl font-bold">
                <span className="text-bullish">{sentiment?.bullish ?? 0}</span>
                {" / "}
                <span className="text-bearish">{sentiment?.bearish ?? 0}</span>
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* News */}
      {newsData && (
        <NewsHighlights
          articles={newsData.highlights ?? []}
          marketSummary={newsData.market_summary}
        />
      )}

      {/* Confluence Signals */}
      {confluence && confluence.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top Confluence Signals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-2 font-medium">Ticker</th>
                    <th className="pb-2 font-medium">Sentiment</th>
                    <th className="pb-2 font-medium">RSI</th>
                    <th className="pb-2 font-medium">MACD</th>
                    <th className="pb-2 font-medium">Score</th>
                    <th className="pb-2 font-medium">Strength</th>
                  </tr>
                </thead>
                <tbody>
                  {confluence.map((s) => (
                    <tr key={s.ticker} className="border-b">
                      <td className="py-2 font-semibold">{s.ticker}</td>
                      <td>
                        <Badge variant={s.sentiment as "bullish" | "bearish" | "neutral" | "mixed"}>
                          {s.sentiment}
                        </Badge>
                      </td>
                      <td>{s.rsi?.toFixed(1) ?? "N/A"}</td>
                      <td>{s.macd_trend ?? "N/A"}</td>
                      <td>{s.technical_score ?? "N/A"}</td>
                      <td>
                        <Badge variant={s.signal_strength === "Strong" ? "default" : "secondary"}>
                          {s.signal_strength}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed Analysis Accordion */}
      {sections && Object.keys(sections).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Detailed Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple">
              {Object.entries(sections).map(([key, content]) => (
                <AccordionItem key={key} value={key}>
                  <AccordionTrigger className="text-sm capitalize">
                    {key.replace(/_/g, " ")}
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="whitespace-pre-wrap text-sm text-muted-foreground">
                      {content}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Weekly Summary */}
      <WeeklySummary />
    </div>
  );
}
