"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useWeeklySummary } from "@/lib/hooks/useReport";
import { Spinner } from "@/components/ui/loading";
import { Calendar, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";

export default function WeeklySummary() {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading, refetch, isRefetching } = useWeeklySummary();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Calendar className="h-4 w-4" />
            7-Day AI Summary
          </CardTitle>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isRefetching}
            >
              <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent>
          {isLoading ? (
            <Spinner className="py-8" />
          ) : data?.summary ? (
            <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm">
              {data.summary}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No weekly summary available.</p>
          )}
        </CardContent>
      )}
    </Card>
  );
}
