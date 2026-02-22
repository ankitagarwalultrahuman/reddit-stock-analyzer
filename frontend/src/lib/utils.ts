import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number, decimals = 2): string {
  if (Math.abs(n) >= 1e7) return `${(n / 1e7).toFixed(decimals)}Cr`;
  if (Math.abs(n) >= 1e5) return `${(n / 1e5).toFixed(decimals)}L`;
  return n.toLocaleString("en-IN", { maximumFractionDigits: decimals });
}

export function formatPercent(n: number | null | undefined): string {
  if (n == null) return "N/A";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function formatPrice(n: number | null | undefined): string {
  if (n == null) return "N/A";
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export const sentimentColor: Record<string, string> = {
  bullish: "text-bullish",
  bearish: "text-bearish",
  neutral: "text-neutral",
  mixed: "text-mixed",
};

export const sentimentBg: Record<string, string> = {
  bullish: "bg-green-100 text-green-800",
  bearish: "bg-red-100 text-red-800",
  neutral: "bg-amber-100 text-amber-800",
  mixed: "bg-purple-100 text-purple-800",
};

export const moodEmoji: Record<string, string> = {
  bullish: "🟢",
  bearish: "🔴",
  neutral: "🟡",
};
