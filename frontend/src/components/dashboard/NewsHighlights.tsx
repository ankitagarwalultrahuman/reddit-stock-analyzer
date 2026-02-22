"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Newspaper } from "lucide-react";

interface NewsArticle {
  headline: string;
  summary: string;
  source: string;
  sentiment_score: number;
}

interface Props {
  articles: NewsArticle[];
  marketSummary?: string;
}

function sentimentLabel(score: number): "bullish" | "bearish" | "neutral" {
  if (score > 0.2) return "bullish";
  if (score < -0.2) return "bearish";
  return "neutral";
}

export default function NewsHighlights({ articles, marketSummary }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Newspaper className="h-4 w-4" />
          News Highlights
        </CardTitle>
      </CardHeader>
      <CardContent>
        {marketSummary && (
          <p className="mb-4 text-sm text-muted-foreground">{marketSummary}</p>
        )}
        <div className="space-y-3">
          {articles.slice(0, 5).map((article, i) => (
            <div key={i} className="flex items-start gap-3 border-b pb-3 last:border-0">
              <div className="flex-1">
                <p className="text-sm font-medium">{article.headline}</p>
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{article.summary}</p>
                <p className="mt-1 text-xs text-muted-foreground">{article.source}</p>
              </div>
              <Badge variant={sentimentLabel(article.sentiment_score)} className="shrink-0">
                {sentimentLabel(article.sentiment_score)}
              </Badge>
            </div>
          ))}
          {articles.length === 0 && (
            <p className="text-sm text-muted-foreground">No news highlights available</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
