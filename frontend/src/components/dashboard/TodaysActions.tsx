"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Eye, ShoppingCart, AlertTriangle, Shield } from "lucide-react";

interface ActionItem {
  ticker: string;
  sentiment: string;
  mentions: number;
  reason: string;
}

interface RiskAlert {
  title: string;
  description: string;
  severity: string;
}

interface Props {
  watchList: ActionItem[];
  considerList: ActionItem[];
  avoidList: ActionItem[];
  riskAlerts: RiskAlert[];
  marketMood: string;
}

function ActionCard({
  title,
  icon: Icon,
  items,
  color,
}: {
  title: string;
  icon: React.ElementType;
  items: ActionItem[];
  color: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Icon className={`h-4 w-4 ${color}`} />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-xs text-muted-foreground">None today</p>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.ticker} className="flex items-start justify-between gap-2">
                <div>
                  <span className="font-semibold text-sm">{item.ticker}</span>
                  <p className="text-xs text-muted-foreground line-clamp-2">{item.reason}</p>
                </div>
                <Badge variant={item.sentiment as "bullish" | "bearish" | "neutral" | "mixed"} className="shrink-0">
                  {item.mentions}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function TodaysActions({ watchList, considerList, avoidList, riskAlerts, marketMood }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Shield className="h-4 w-4 text-blue-500" />
            Market Mood
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <span className="text-2xl">
              {marketMood === "bullish" ? "🟢" : marketMood === "bearish" ? "🔴" : "🟡"}
            </span>
            <span className="text-lg font-semibold capitalize">{marketMood}</span>
          </div>
          {riskAlerts.length > 0 && (
            <div className="mt-3 space-y-1">
              {riskAlerts.slice(0, 2).map((alert, i) => (
                <p key={i} className="text-xs text-muted-foreground">
                  <span className={alert.severity === "high" ? "text-red-500" : "text-amber-500"}>!</span>{" "}
                  {alert.title}
                </p>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <ActionCard title="Watch List" icon={Eye} items={watchList} color="text-green-500" />
      <ActionCard title="Consider Buying" icon={ShoppingCart} items={considerList} color="text-blue-500" />
      <ActionCard title="Risk / Avoid" icon={AlertTriangle} items={avoidList} color="text-red-500" />
    </div>
  );
}
