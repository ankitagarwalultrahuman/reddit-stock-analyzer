// Report types
interface ReportData {
  date: string;
  content: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

interface SessionData {
  am: { content: string; metadata: Record<string, unknown> } | null;
  pm: { content: string; metadata: Record<string, unknown> } | null;
  has_both: boolean;
}

interface ActionsData {
  watch_list: ActionItem[];
  consider_list: ActionItem[];
  avoid_list: ActionItem[];
  risk_alerts: RiskAlert[];
  market_mood: string;
  focus_summary: string;
}

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

interface StockMention {
  ticker: string;
  post_count: number;
  comment_count: number;
  sentiment: string;
  total_mentions: number;
}

interface Insight {
  rank: number;
  ticker: string;
  description: string;
  post_count: number;
  comment_count: number;
  sentiment: string;
  key_points: string;
  total_mentions: number;
}

interface SentimentDistribution {
  bullish: number;
  bearish: number;
  neutral: number;
  mixed: number;
}

interface ComparisonData {
  content: string;
  has_comparison: boolean;
}

// Stock types
interface StockHistoryRecord {
  Date?: string;
  index?: string;
  Open: number;
  High: number;
  Low: number;
  Close: number;
  Volume: number;
}

interface TechnicalsResponse {
  success: boolean;
  ticker: string;
  current_price: number;
  technicals: Technicals;
  history: StockHistoryRecord[];
  error?: string;
}

interface Technicals {
  rsi: number | null;
  rsi_signal: string | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  macd_trend: string | null;
  ema_20: number | null;
  ema_50: number | null;
  ema_200: number | null;
  ma_trend: string | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  bb_position: string | null;
  bb_width: number | null;
  atr: number | null;
  atr_percent: number | null;
  volatility_level: string | null;
  volume: number | null;
  volume_avg: number | null;
  volume_ratio: number | null;
  volume_signal: string | null;
  adx: number | null;
  adx_signal: string;
  stoch_rsi_k: number | null;
  stoch_rsi_d: number | null;
  stoch_rsi_signal: string;
  technical_score: number | null;
  technical_bias: string | null;
  week_52_high: number | null;
  week_52_low: number | null;
  pct_from_52w_high: number | null;
  current_price: number;
  divergence: string | null;
  divergence_strength: string | null;
}

// Portfolio types
interface Holding {
  ticker: string;
  quantity: number;
  avg_price: number;
  current_price?: number;
  pnl?: number;
  pnl_percent?: number;
}

interface GrowwHolding {
  trading_symbol: string;
  quantity: number;
  average_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
  current_value: number;
  invested_value: number;
}

interface PortfolioAnalysis {
  holdings: Array<{
    ticker: string;
    sentiment: string;
    alignment: string;
    current_price: number;
    change_percent: number;
  }>;
  summary: string;
}

// Screener types
interface ScreenerResult {
  ticker: string;
  current_price: number;
  matched_criteria: string[];
  score: number;
  rsi: number | null;
  macd_trend: string | null;
  ma_trend: string | null;
  volume_signal: string | null;
  technical_bias: string | null;
}

interface StrategyInfo {
  name: string;
  description: string;
}

// Swing types
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
  technical_summary: Record<string, unknown>;
  relative_strength: number;
}

// Task types
interface TaskResult<T = unknown> {
  status: "running" | "complete" | "error" | "not_found";
  result: T | null;
  error: string | null;
  created_at?: string;
}

// Signal types
interface ConfluenceSignal {
  ticker: string;
  sentiment: string;
  mentions: number;
  current_price: number;
  rsi: number | null;
  rsi_signal: string | null;
  macd_trend: string | null;
  ma_trend: string | null;
  technical_score: number | null;
  technical_bias: string | null;
  confluence_score: number;
  aligned_signals: string[];
  signal_strength: string;
}

interface AccuracyStats {
  total_signals: number;
  accuracy_1d: number;
  accuracy_3d: number;
  accuracy_5d: number;
  bullish_accuracy: number;
  bearish_accuracy: number;
  avg_return_1d: number;
  avg_return_3d: number;
  avg_return_5d: number;
}

// News types
interface NewsHighlights {
  highlights: NewsArticle[];
  market_summary: string;
  key_alerts: string[];
  sentiment_divergences?: Array<{
    ticker: string;
    reddit_sentiment: string;
    news_sentiment: string;
  }>;
}

interface NewsArticle {
  headline: string;
  summary: string;
  source: string;
  url: string;
  published_at: string;
  sentiment_score: number;
  category: string;
}

// Weekly/Nifty types
interface NiftyPerformance {
  current_price: number;
  week_change: number;
  month_change: number;
  two_week_change?: number;
  four_week_change?: number;
}

// Sector types
interface SectorData {
  sector: string;
  stock_count: number;
  avg_return_1w: number;
  avg_return_1m: number;
  avg_rsi: number;
  momentum_score: number;
  momentum_trend: string;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
}
