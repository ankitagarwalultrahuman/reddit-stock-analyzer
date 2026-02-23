"""
Weekly Market Pulse Analysis Module

Generates weekly market analysis reports for swing traders including:
- Top gaining/losing sectors
- Stocks breaking out of consolidation
- Relative strength leaders
- FII/DII flow analysis
- Key support/resistance levels approaching
"""

import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from stock_history import fetch_stock_history, get_current_price
from technical_analysis import get_technical_analysis, TechnicalSignals
from sector_tracker import analyze_all_sectors, SectorMetrics
from watchlist_manager import NIFTY50_STOCKS, SECTOR_STOCKS, get_sector_for_stock
from config import SCREENER_RSI_OVERSOLD, RSI_OVERBOUGHT, RS_LOOKBACK_DAYS, RS_BENCHMARK


@dataclass
class StockWeeklyMetrics:
    """Weekly metrics for a single stock over 7 weeks."""
    ticker: str
    sector: str
    current_price: float
    week_change_pct: float      # 1 week (5 days)
    two_week_change_pct: float  # 2 weeks (10 days)
    four_week_change_pct: float # 4 weeks (20 days)
    month_change_pct: float     # 6 weeks (30 days) - broader view
    volume_ratio: float         # vs 20-day average
    rsi: float
    macd_signal: str
    technical_bias: str
    relative_strength: float    # vs NIFTY over 4 weeks
    near_support: bool
    near_resistance: bool
    weekly_trend: str           # "up", "down", "sideways" based on multi-week
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    trend_strength: str = "moderate"  # "strong", "moderate", "weak"
    consolidating: bool = False
    breakout_candidate: bool = False
    breakdown_candidate: bool = False  # Price breaking support
    # 52-week high/low data
    week_52_high: float = 0.0
    week_52_low: float = 0.0
    pct_from_52w_high: float = 0.0
    near_52w_high: bool = False


@dataclass
class WeeklyPulseReport:
    """Complete weekly market pulse report."""
    report_date: datetime
    week_start: datetime
    week_end: datetime

    # Market overview - multi-week NIFTY performance
    nifty_week_change: float       # 1 week (5 days)
    nifty_two_week_change: float   # 2 weeks (10 days)
    nifty_four_week_change: float  # 4 weeks (20 days)
    nifty_month_change: float      # 6 weeks (30 days)
    market_breadth: dict  # advances, declines, unchanged

    # Sector analysis
    top_sectors: list  # Top 3 performing sectors
    bottom_sectors: list  # Bottom 3 performing sectors
    sector_metrics: list[SectorMetrics]

    # Stock highlights
    top_gainers: list[StockWeeklyMetrics]
    top_losers: list[StockWeeklyMetrics]
    breakout_candidates: list[StockWeeklyMetrics]
    oversold_stocks: list[StockWeeklyMetrics]  # RSI < 35
    overbought_stocks: list[StockWeeklyMetrics]  # RSI > 70
    rs_leaders: list[StockWeeklyMetrics]  # High relative strength

    # FII/DII data (if available)
    fii_net_value: Optional[float] = None
    dii_net_value: Optional[float] = None
    fii_trend: str = "N/A"  # buying/selling/neutral

    # Key insights
    insights: list[str] = field(default_factory=list)


def calculate_relative_strength(ticker: str, benchmark_ticker: str = RS_BENCHMARK, days: int = RS_LOOKBACK_DAYS) -> float:
    """
    Calculate relative strength of a stock vs benchmark (NIFTY).

    Returns:
        RS value > 0 means outperforming, < 0 means underperforming
    """
    try:
        import yfinance as yf

        # Get stock data (extra buffer for trading holidays)
        stock_df = fetch_stock_history(ticker, days=days + 10)
        if stock_df.empty or len(stock_df) < days:
            return 0.0

        # Get benchmark data
        benchmark = yf.Ticker(benchmark_ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)
        benchmark_df = benchmark.history(start=start_date, end=end_date)

        if benchmark_df.empty or len(benchmark_df) < days:
            return 0.0

        # Calculate returns for the period
        stock_return = ((stock_df['Close'].iloc[-1] / stock_df['Close'].iloc[0]) - 1) * 100
        benchmark_return = ((benchmark_df['Close'].iloc[-1] / benchmark_df['Close'].iloc[0]) - 1) * 100

        # Relative strength = stock return - benchmark return
        return round(stock_return - benchmark_return, 2)

    except Exception as e:
        print(f"Error calculating RS for {ticker}: {e}")
        return 0.0


def find_support_resistance(df: pd.DataFrame, lookback: int = 20) -> tuple[float, float]:
    """
    Find support and resistance levels using pivot points.

    Returns:
        (support_level, resistance_level)
    """
    if df.empty or len(df) < lookback:
        return (0.0, 0.0)

    recent_df = df.tail(lookback)

    # Find swing lows (support) and swing highs (resistance)
    highs = recent_df['High'].values
    lows = recent_df['Low'].values

    # Simple approach: use recent high as resistance, recent low as support
    resistance = float(recent_df['High'].max())
    support = float(recent_df['Low'].min())

    return (round(support, 2), round(resistance, 2))


def detect_consolidation(df: pd.DataFrame, days: int = 10, threshold_pct: float = 5.0) -> bool:
    """
    Detect if stock is consolidating (trading in tight range).

    A stock is consolidating if the range (high-low) over the period
    is less than threshold_pct of the average price.
    """
    if df.empty or len(df) < days:
        return False

    recent_df = df.tail(days)
    high = recent_df['High'].max()
    low = recent_df['Low'].min()
    avg_price = recent_df['Close'].mean()

    range_pct = ((high - low) / avg_price) * 100

    return range_pct < threshold_pct


def detect_breakout_candidate(df: pd.DataFrame, current_price: float, resistance: float) -> bool:
    """
    Detect if stock is a breakout candidate.

    Criteria:
    - Price within 3% of resistance
    - Volume increasing
    """
    if resistance == 0:
        return False

    distance_to_resistance = ((resistance - current_price) / current_price) * 100

    # Within 3% of resistance
    return 0 < distance_to_resistance < 3


def analyze_stock_weekly(ticker: str) -> Optional[StockWeeklyMetrics]:
    """Analyze a single stock for weekly metrics using 7 weeks of data."""
    try:
        # Get 7 weeks of historical data (50 trading days)
        df = fetch_stock_history(ticker, days=50, force_refresh=True)
        if df is None or df.empty:
            print(f"[{ticker}] No data returned from fetch_stock_history")
            return None
        if len(df) < 10:
            print(f"[{ticker}] Insufficient data: only {len(df)} rows")
            return None

        # Get current price
        price_data = get_current_price(ticker)
        if not price_data.get("success"):
            current_price = float(df['Close'].iloc[-1])
        else:
            current_price = price_data["current_price"]

        # Calculate weekly change (1 week = 5 trading days)
        if len(df) >= 5:
            week_ago_price = float(df['Close'].iloc[-5])
            week_change = ((current_price - week_ago_price) / week_ago_price) * 100
        else:
            week_change = 0.0

        # Calculate 2-week change (10 trading days)
        two_week_change = 0.0
        if len(df) >= 10:
            two_week_ago_price = float(df['Close'].iloc[-10])
            two_week_change = ((current_price - two_week_ago_price) / two_week_ago_price) * 100

        # Calculate 4-week change (20 trading days)
        four_week_change = 0.0
        if len(df) >= 20:
            four_week_ago_price = float(df['Close'].iloc[-20])
            four_week_change = ((current_price - four_week_ago_price) / four_week_ago_price) * 100

        # Calculate 6-week change (30 trading days) - use this as month_change for broader view
        if len(df) >= 30:
            six_week_ago_price = float(df['Close'].iloc[-30])
            month_change = ((current_price - six_week_ago_price) / six_week_ago_price) * 100
        elif len(df) >= 20:
            month_change = four_week_change
        else:
            month_change = 0.0

        # Volume ratio (compare recent week vs 4-week average)
        if 'Volume' in df.columns:
            current_week_vol = float(df['Volume'].tail(5).mean())
            avg_vol = float(df['Volume'].tail(20).mean())
            volume_ratio = current_week_vol / avg_vol if avg_vol > 0 else 1.0
        else:
            volume_ratio = 1.0

        # Technical analysis - pass the DataFrame we already have
        tech = get_technical_analysis(df, ticker)
        rsi = tech.rsi if tech else 50
        macd_signal = tech.macd_trend if tech else "neutral"
        technical_bias = tech.technical_bias if tech else "neutral"

        # Support/Resistance using 6 weeks of data
        support, resistance = find_support_resistance(df, lookback=30)

        # Near support/resistance (within 3%)
        near_support = support > 0 and ((current_price - support) / current_price) < 0.03
        near_resistance = resistance > 0 and ((resistance - current_price) / current_price) < 0.03

        # Consolidation detection (over 2 weeks)
        consolidating = detect_consolidation(df, days=10, threshold_pct=8.0)
        breakout_candidate = detect_breakout_candidate(df, current_price, resistance)

        # Relative strength vs NIFTY over 4 weeks
        rs = calculate_relative_strength(ticker, days=20)

        # Determine weekly trend based on multi-week performance (lowered from 5% to 2%)
        if four_week_change > 2 and week_change > 0:
            weekly_trend = "up"
        elif four_week_change < -2 and week_change < 0:
            weekly_trend = "down"
        else:
            weekly_trend = "sideways"

        # Calculate trend strength
        abs_four_week = abs(four_week_change)
        if abs_four_week > 10:
            trend_strength = "strong"
        elif abs_four_week > 5:
            trend_strength = "moderate"
        elif abs_four_week > 2:
            trend_strength = "weak"
        else:
            trend_strength = "weak"

        # Breakdown detection: price within 3% above support or already below
        breakdown_candidate = False
        if support > 0 and current_price > 0:
            pct_above_support = ((current_price - support) / support) * 100
            # Price is within 3% above support and trend is down
            breakdown_candidate = (pct_above_support < 3 and weekly_trend == "down"
                                   and volume_ratio > 1.2)

        # Get sector
        sector = get_sector_for_stock(ticker) or "Unknown"

        return StockWeeklyMetrics(
            ticker=ticker,
            sector=sector,
            current_price=round(current_price, 2),
            week_change_pct=round(week_change, 2),
            two_week_change_pct=round(two_week_change, 2),
            four_week_change_pct=round(four_week_change, 2),
            month_change_pct=round(month_change, 2),
            volume_ratio=round(volume_ratio, 2),
            rsi=round(rsi, 1) if rsi else 50,
            macd_signal=macd_signal,
            technical_bias=technical_bias,
            relative_strength=rs,
            near_support=near_support,
            near_resistance=near_resistance,
            weekly_trend=weekly_trend,
            support_level=support,
            resistance_level=resistance,
            trend_strength=trend_strength,
            consolidating=consolidating,
            breakout_candidate=breakout_candidate or (consolidating and near_resistance),
            breakdown_candidate=breakdown_candidate,
            # 52-week high/low from technical analysis
            week_52_high=tech.week_52_high if tech and tech.week_52_high else 0.0,
            week_52_low=tech.week_52_low if tech and tech.week_52_low else 0.0,
            pct_from_52w_high=tech.pct_from_52w_high if tech and tech.pct_from_52w_high else 0.0,
            near_52w_high=tech.near_52w_high if tech else False
        )

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None


def get_nifty_performance() -> dict:
    """Get NIFTY 50 index performance over 7 weeks."""
    try:
        import yfinance as yf

        nifty = yf.Ticker("^NSEI")
        df = nifty.history(period="3mo")  # Get 3 months for 7+ weeks of data

        if df.empty:
            return {"week_change": 0, "two_week_change": 0, "four_week_change": 0, "six_week_change": 0}

        current = float(df['Close'].iloc[-1])

        # 1 Week change (5 trading days)
        week_change = 0
        if len(df) >= 5:
            week_ago = float(df['Close'].iloc[-5])
            week_change = ((current - week_ago) / week_ago) * 100

        # 2 Week change (10 trading days)
        two_week_change = 0
        if len(df) >= 10:
            two_week_ago = float(df['Close'].iloc[-10])
            two_week_change = ((current - two_week_ago) / two_week_ago) * 100

        # 4 Week change (20 trading days)
        four_week_change = 0
        if len(df) >= 20:
            four_week_ago = float(df['Close'].iloc[-20])
            four_week_change = ((current - four_week_ago) / four_week_ago) * 100

        # 6 Week change (30 trading days)
        six_week_change = 0
        if len(df) >= 30:
            six_week_ago = float(df['Close'].iloc[-30])
            six_week_change = ((current - six_week_ago) / six_week_ago) * 100

        return {
            "current": round(current, 2),
            "week_change": round(week_change, 2),
            "two_week_change": round(two_week_change, 2),
            "four_week_change": round(four_week_change, 2),
            "six_week_change": round(six_week_change, 2),
            "month_change": round(six_week_change, 2)  # Alias for compatibility
        }

    except Exception as e:
        print(f"Error fetching NIFTY: {e}")
        return {"week_change": 0, "two_week_change": 0, "four_week_change": 0, "six_week_change": 0, "month_change": 0}


def get_fii_dii_data() -> dict:
    """
    Fetch FII/DII data.
    Currently returns stub data - FII/DII integration requires
    a reliable data source (nsepython/nselib are unreliable).
    """
    return {
        "fii_net": None,
        "dii_net": None,
        "fii_trend": "N/A",
        "available": False
    }


def generate_weekly_pulse(
    stocks: list[str] = None,
    max_workers: int = 5
) -> WeeklyPulseReport:
    """
    Generate comprehensive weekly market pulse report.

    Args:
        stocks: List of stocks to analyze (defaults to NIFTY50)
        max_workers: Parallel workers for analysis

    Returns:
        WeeklyPulseReport with all analysis
    """
    if stocks is None:
        stocks = NIFTY50_STOCKS

    print(f"Generating weekly pulse for {len(stocks)} stocks...")

    # Get NIFTY performance
    nifty_perf = get_nifty_performance()
    print(f"NIFTY Performance: 1W={nifty_perf.get('week_change', 0):.2f}%, 2W={nifty_perf.get('two_week_change', 0):.2f}%, 4W={nifty_perf.get('four_week_change', 0):.2f}%, 6W={nifty_perf.get('month_change', 0):.2f}%")

    # Analyze all stocks in parallel
    stock_metrics = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_stock_weekly, ticker): ticker for ticker in stocks}
        for future in as_completed(futures):
            result = future.result()
            if result:
                stock_metrics.append(result)

    print(f"Analyzed {len(stock_metrics)} stocks successfully")

    # Get sector analysis
    sector_metrics = analyze_all_sectors(max_workers=max_workers)

    # Sort sectors by performance
    sorted_sectors = sorted(sector_metrics, key=lambda x: x.avg_return_5d, reverse=True)
    top_sectors = sorted_sectors[:3]
    bottom_sectors = sorted_sectors[-3:]

    # Categorize stocks
    top_gainers = sorted(stock_metrics, key=lambda x: x.week_change_pct, reverse=True)[:10]
    top_losers = sorted(stock_metrics, key=lambda x: x.week_change_pct)[:10]

    breakout_candidates = [s for s in stock_metrics if s.breakout_candidate]
    breakout_candidates = sorted(breakout_candidates, key=lambda x: x.relative_strength, reverse=True)[:10]

    oversold_stocks = [s for s in stock_metrics if s.rsi < SCREENER_RSI_OVERSOLD]
    oversold_stocks = sorted(oversold_stocks, key=lambda x: x.rsi)[:10]

    overbought_stocks = [s for s in stock_metrics if s.rsi > RSI_OVERBOUGHT]
    overbought_stocks = sorted(overbought_stocks, key=lambda x: x.rsi, reverse=True)[:10]

    rs_leaders = sorted(stock_metrics, key=lambda x: x.relative_strength, reverse=True)[:10]

    # Calculate market breadth (mutually exclusive categories)
    unchanged = len([s for s in stock_metrics if abs(s.week_change_pct) < 0.01])
    advances = len([s for s in stock_metrics if s.week_change_pct >= 0.01])
    declines = len([s for s in stock_metrics if s.week_change_pct <= -0.01])

    # Get FII/DII data
    fii_dii = get_fii_dii_data()

    # Generate insights
    insights = generate_insights(
        nifty_perf, top_sectors, bottom_sectors,
        breakout_candidates, oversold_stocks, rs_leaders,
        advances, declines
    )

    return WeeklyPulseReport(
        report_date=datetime.now(),
        week_start=datetime.now() - timedelta(days=7),
        week_end=datetime.now(),
        nifty_week_change=nifty_perf.get("week_change", 0),
        nifty_two_week_change=nifty_perf.get("two_week_change", 0),
        nifty_four_week_change=nifty_perf.get("four_week_change", 0),
        nifty_month_change=nifty_perf.get("month_change", 0),
        market_breadth={"advances": advances, "declines": declines, "unchanged": unchanged},
        top_sectors=top_sectors,
        bottom_sectors=bottom_sectors,
        sector_metrics=sector_metrics,
        top_gainers=top_gainers,
        top_losers=top_losers,
        breakout_candidates=breakout_candidates,
        oversold_stocks=oversold_stocks,
        overbought_stocks=overbought_stocks,
        rs_leaders=rs_leaders,
        fii_net_value=fii_dii.get("fii_net"),
        dii_net_value=fii_dii.get("dii_net"),
        fii_trend=fii_dii.get("fii_trend", "N/A"),
        insights=insights
    )


def generate_insights(
    nifty_perf: dict,
    top_sectors: list,
    bottom_sectors: list,
    breakout_candidates: list,
    oversold_stocks: list,
    rs_leaders: list,
    advances: int,
    declines: int
) -> list[str]:
    """Generate actionable insights from the analysis."""
    insights = []

    # Market direction
    nifty_change = nifty_perf.get("week_change", 0)
    if nifty_change > 2:
        insights.append(f"NIFTY up {nifty_change:.1f}% this week - bullish momentum, look for breakout plays")
    elif nifty_change < -2:
        insights.append(f"NIFTY down {nifty_change:.1f}% this week - defensive mode, focus on oversold bounces")
    else:
        insights.append(f"NIFTY flat ({nifty_change:.1f}%) - range-bound market, stock-specific opportunities")

    # Market breadth
    breadth_ratio = advances / (advances + declines) if (advances + declines) > 0 else 0.5
    if breadth_ratio > 0.65:
        insights.append(f"Strong breadth: {advances} advances vs {declines} declines - broad-based rally")
    elif breadth_ratio < 0.35:
        insights.append(f"Weak breadth: {advances} advances vs {declines} declines - selective selling")

    # Sector rotation
    if top_sectors:
        top_sector_names = [s.sector for s in top_sectors[:2]]
        insights.append(f"Money flowing into: {', '.join(top_sector_names)}")

    if bottom_sectors:
        bottom_sector_names = [s.sector for s in bottom_sectors[:2]]
        insights.append(f"Avoid/Short: {', '.join(bottom_sector_names)} showing weakness")

    # Breakout opportunities
    if breakout_candidates:
        tickers = [s.ticker for s in breakout_candidates[:3]]
        insights.append(f"Breakout watch: {', '.join(tickers)} near resistance with momentum")

    # Oversold bounces
    if oversold_stocks:
        tickers = [s.ticker for s in oversold_stocks[:3]]
        insights.append(f"Oversold bounce candidates: {', '.join(tickers)} (RSI < 35)")

    # RS Leaders
    if rs_leaders:
        tickers = [s.ticker for s in rs_leaders[:3]]
        insights.append(f"Relative strength leaders: {', '.join(tickers)} outperforming NIFTY")

    return insights


def get_weekly_pulse_summary(report: WeeklyPulseReport) -> str:
    """Generate text summary of weekly pulse report."""
    lines = [
        f"=== WEEKLY MARKET PULSE - {report.report_date.strftime('%d %b %Y')} ===",
        "",
        f"NIFTY: {report.nifty_week_change:+.1f}% (Week) | {report.nifty_month_change:+.1f}% (Month)",
        f"Breadth: {report.market_breadth['advances']} up / {report.market_breadth['declines']} down",
        "",
        "TOP SECTORS:",
    ]

    for sector in report.top_sectors[:3]:
        lines.append(f"  {sector.sector}: {sector.avg_return_5d:+.1f}% (5D)")

    lines.append("")
    lines.append("WEAK SECTORS:")
    for sector in report.bottom_sectors[:3]:
        lines.append(f"  {sector.sector}: {sector.avg_return_5d:+.1f}% (5D)")

    lines.append("")
    lines.append("KEY INSIGHTS:")
    for insight in report.insights:
        lines.append(f"  • {insight}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test run
    report = generate_weekly_pulse(stocks=NIFTY50_STOCKS[:10])  # Test with 10 stocks
    print(get_weekly_pulse_summary(report))
