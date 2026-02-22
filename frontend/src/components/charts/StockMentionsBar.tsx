"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const COLORS: Record<string, string> = {
  bullish: "#22c55e",
  bearish: "#ef4444",
  neutral: "#f59e0b",
  mixed: "#8b5cf6",
};

interface Props {
  data: Array<{
    ticker: string;
    total_mentions: number;
    sentiment: string;
  }>;
}

export default function StockMentionsBar({ data }: Props) {
  const sorted = [...data].sort((a, b) => b.total_mentions - a.total_mentions).slice(0, 10);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 60, right: 20, top: 5, bottom: 5 }}>
        <XAxis type="number" />
        <YAxis type="category" dataKey="ticker" width={55} tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value) => [value, "Mentions"]}
          contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        <Bar dataKey="total_mentions" radius={[0, 4, 4, 0]}>
          {sorted.map((entry, i) => (
            <Cell key={i} fill={COLORS[entry.sentiment] || COLORS.neutral} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
