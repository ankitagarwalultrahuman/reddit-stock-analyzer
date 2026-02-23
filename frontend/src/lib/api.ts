const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// Reports
export const api = {
  // Reports
  getReportDates: () => fetchAPI<string[]>("/api/reports/dates"),
  getReport: (date: string) => fetchAPI<ReportData>(`/api/reports/${date}`),
  getSessions: (date: string) => fetchAPI<SessionData>(`/api/reports/${date}/sessions`),
  getActions: (date: string) => fetchAPI<ActionsData>(`/api/reports/${date}/actions`),
  getStocks: (date: string) => fetchAPI<StockMention[]>(`/api/reports/${date}/stocks`),
  getInsights: (date: string) => fetchAPI<Insight[]>(`/api/reports/${date}/insights`),
  getSections: (date: string) => fetchAPI<Record<string, string>>(`/api/reports/${date}/sections`),
  getSentiment: (date: string) => fetchAPI<SentimentDistribution>(`/api/reports/${date}/sentiment`),
  getComparison: (date: string) => fetchAPI<ComparisonData>(`/api/reports/${date}/comparison`),
  getWeeklySummary: () => fetchAPI<{ summary: string }>("/api/reports/weekly-summary"),

  // Stocks
  getStockHistory: (ticker: string, days = 30) =>
    fetchAPI<StockHistoryRecord[]>(`/api/stocks/${ticker}/history?days=${days}`),
  getStockTechnicals: (ticker: string, days = 60) =>
    fetchAPI<TechnicalsResponse>(`/api/stocks/${ticker}/technicals?days=${days}`),
  getMultipleStocks: (tickers: string[], days = 30) =>
    fetchAPI<Record<string, StockHistoryRecord[]>>(
      `/api/stocks/multiple?tickers=${tickers.join(",")}&days=${days}`
    ),

  // Portfolio
  getHoldings: () => fetchAPI<Holding[]>("/api/portfolio/holdings"),
  addHolding: (ticker: string, quantity: number, avg_price: number) =>
    fetchAPI<Holding>("/api/portfolio/holdings", {
      method: "POST",
      body: JSON.stringify({ ticker, quantity, avg_price }),
    }),
  removeHolding: (ticker: string) =>
    fetchAPI<{ success: boolean }>(`/api/portfolio/holdings/${ticker}`, { method: "DELETE" }),
  getPortfolioAnalysis: () => fetchAPI<PortfolioAnalysis>("/api/portfolio/analysis"),
  getGrowwHoldings: () => fetchAPI<GrowwHolding[]>("/api/portfolio/groww/holdings"),

  // Screener (async)
  startScan: (watchlist: string, strategy: string, min_matches: number) =>
    fetchAPI<{ task_id: string }>("/api/screener/scan", {
      method: "POST",
      body: JSON.stringify({ watchlist, strategy, min_matches }),
    }),
  getScanResult: (taskId: string) => fetchAPI<TaskResult>(`/api/screener/scan/${taskId}`),
  getStrategies: () => fetchAPI<Record<string, StrategyInfo>>("/api/screener/strategies"),

  // Swing (async)
  startSwingScan: (watchlist: string, min_score: number) =>
    fetchAPI<{ task_id: string }>("/api/swing/scan", {
      method: "POST",
      body: JSON.stringify({ watchlist, min_score }),
    }),
  getSwingResult: (taskId: string) => fetchAPI<TaskResult>(`/api/swing/scan/${taskId}`),

  // Sectors (async)
  startSectorAnalysis: () =>
    fetchAPI<{ task_id: string }>("/api/sectors/analyze", { method: "POST" }),
  getSectorResult: (taskId: string) => fetchAPI<TaskResult>(`/api/sectors/analyze/${taskId}`),

  // ETF (async)
  startETFAnalysis: () =>
    fetchAPI<{ task_id: string }>("/api/etf/analyze", { method: "POST" }),
  getETFResult: (taskId: string) => fetchAPI<TaskResult>(`/api/etf/analyze/${taskId}`),

  // Weekly (async)
  startWeeklyPulse: (watchlist = "NIFTY50") =>
    fetchAPI<{ task_id: string }>("/api/weekly/pulse", {
      method: "POST",
      body: JSON.stringify({ watchlist }),
    }),
  getWeeklyResult: (taskId: string) => fetchAPI<TaskResult>(`/api/weekly/pulse/${taskId}`),
  getNiftyPerformance: () => fetchAPI<NiftyPerformance>("/api/weekly/nifty"),

  // Signals
  getConfluenceSignals: (date?: string, limit = 5) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (date) params.set("report_date", date);
    return fetchAPI<ConfluenceSignal[]>(`/api/signals/confluence?${params}`);
  },
  getAccuracyStats: (days = 30) =>
    fetchAPI<AccuracyStats>(`/api/signals/accuracy?days=${days}`),

  // News
  getNewsHighlights: () => fetchAPI<NewsHighlights>("/api/news/highlights"),

  // Alerts (async)
  startMovementScan: (tickers: string[], threshold = 1.0) =>
    fetchAPI<{ task_id: string }>("/api/alerts/movement/scan", {
      method: "POST",
      body: JSON.stringify({ tickers, threshold }),
    }),
  getMovementResult: (taskId: string) =>
    fetchAPI<TaskResult>(`/api/alerts/movement/scan/${taskId}`),
  testTelegram: (message: string) =>
    fetchAPI<{ success: boolean }>("/api/alerts/telegram/test", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  testSms: (message: string) =>
    fetchAPI<{ success: boolean }>("/api/alerts/sms/test", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
