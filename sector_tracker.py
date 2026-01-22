"""
Sector Rotation Tracker - Tracks momentum and rotation across market sectors.

Provides:
- Sector performance comparison
- Momentum scoring for each sector
- Rotation signals (which sectors are gaining/losing strength)
- Historical sector performance tracking
"""

import concurrent.futures
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

from watchlist_manager import SECTOR_STOCKS, ALL_SECTORS, get_sector_stocks
from stock_history import fetch_stock_history, calculate_performance_metrics
from technical_analysis import get_technical_analysis, TechnicalSignals


# Sector index ETFs for direct tracking (if available)
SECTOR_ETFS = {
    "Banking": "BANKBEES",
    "IT": "ITBEES",
    "Energy": "OILGASBEES",
    "Infrastructure": "INFRABEES",
    # Add more as available
}


@dataclass
class SectorMetrics:
    """Performance and technical metrics for a sector."""
    sector: str
    stock_count: int

    # Performance metrics (averaged across stocks)
    avg_return_1d: float = 0.0
    avg_return_5d: float = 0.0
    avg_return_20d: float = 0.0
    avg_return_60d: float = 0.0

    # Technical metrics (averaged)
    avg_rsi: float = 50.0
    bullish_count: int = 0  # Stocks with bullish technical bias
    bearish_count: int = 0  # Stocks with bearish technical bias
    neutral_count: int = 0

    # Momentum score (0-100)
    momentum_score: float = 50.0
    momentum_trend: str = "neutral"  # "gaining", "losing", "neutral"

    # Relative strength
    relative_strength: float = 0.0  # vs NIFTY50 benchmark

    # Top/bottom performers in sector
    top_stocks: list = None
    bottom_stocks: list = None

    def __post_init__(self):
        if self.top_stocks is None:
            self.top_stocks = []
        if self.bottom_stocks is None:
            self.bottom_stocks = []


@dataclass
class StockPerformance:
    """Performance data for a single stock."""
    ticker: str
    current_price: float
    return_1d: float
    return_5d: float
    return_20d: float
    rsi: Optional[float]
    technical_bias: str


def analyze_stock_for_sector(ticker: str) -> Optional[StockPerformance]:
    """Analyze a single stock for sector analysis."""
    try:
        df = fetch_stock_history(ticker, days=60)
        if df.empty or len(df) < 20:
            return None

        # Get technical analysis
        signals = get_technical_analysis(df, ticker)

        # Calculate returns
        close = df['Close']
        current = float(close.iloc[-1])  # Convert to native Python float

        return_1d = ((current / float(close.iloc[-2])) - 1) * 100 if len(close) > 1 else 0
        return_5d = ((current / float(close.iloc[-5])) - 1) * 100 if len(close) > 5 else 0
        return_20d = ((current / float(close.iloc[-20])) - 1) * 100 if len(close) > 20 else 0

        return StockPerformance(
            ticker=ticker,
            current_price=round(current, 2),
            return_1d=round(float(return_1d), 2),
            return_5d=round(float(return_5d), 2),
            return_20d=round(float(return_20d), 2),
            rsi=float(signals.rsi) if signals.rsi else None,
            technical_bias=signals.technical_bias or "neutral",
        )

    except Exception as e:
        # Silently skip failed tickers
        return None


def analyze_sector(sector: str, max_workers: int = 5) -> SectorMetrics:
    """
    Analyze all stocks in a sector.

    Args:
        sector: Sector name
        max_workers: Max parallel workers

    Returns:
        SectorMetrics object with aggregated data
    """
    stocks = get_sector_stocks(sector)
    if not stocks:
        return SectorMetrics(sector=sector, stock_count=0)

    # Analyze stocks in parallel
    performances = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_for_sector, ticker): ticker
            for ticker in stocks
        }

        for future in concurrent.futures.as_completed(future_to_ticker):
            result = future.result()
            if result:
                performances.append(result)

    if not performances:
        return SectorMetrics(sector=sector, stock_count=len(stocks))

    # Calculate averages
    avg_1d = sum(p.return_1d for p in performances) / len(performances)
    avg_5d = sum(p.return_5d for p in performances) / len(performances)
    avg_20d = sum(p.return_20d for p in performances) / len(performances)
    avg_rsi = sum(p.rsi for p in performances if p.rsi) / len([p for p in performances if p.rsi]) if any(p.rsi for p in performances) else 50

    # Count technical biases
    bullish = sum(1 for p in performances if p.technical_bias == "bullish")
    bearish = sum(1 for p in performances if p.technical_bias == "bearish")
    neutral = len(performances) - bullish - bearish

    # Calculate momentum score (0-100)
    # Based on: short-term returns, RSI position, and technical bias ratio
    momentum_score = 50  # Base

    # Return contribution (max +/- 25)
    if avg_5d > 0:
        momentum_score += min(avg_5d * 2.5, 25)
    else:
        momentum_score += max(avg_5d * 2.5, -25)

    # RSI contribution (max +/- 15)
    if avg_rsi < 40:
        momentum_score -= 15  # Oversold = losing momentum recently
    elif avg_rsi > 60:
        momentum_score += 15  # Strong momentum

    # Bias contribution (max +/- 10)
    if len(performances) > 0:
        bullish_ratio = bullish / len(performances)
        momentum_score += (bullish_ratio - 0.5) * 20

    momentum_score = max(0, min(100, momentum_score))

    # Determine trend
    if momentum_score > 60:
        momentum_trend = "gaining"
    elif momentum_score < 40:
        momentum_trend = "losing"
    else:
        momentum_trend = "neutral"

    # Sort for top/bottom performers (ensure native Python types)
    sorted_by_return = sorted(performances, key=lambda x: x.return_5d, reverse=True)
    top_stocks = [(p.ticker, float(p.return_5d)) for p in sorted_by_return[:3]]
    bottom_stocks = [(p.ticker, float(p.return_5d)) for p in sorted_by_return[-3:]]

    return SectorMetrics(
        sector=sector,
        stock_count=len(performances),
        avg_return_1d=round(avg_1d, 2),
        avg_return_5d=round(avg_5d, 2),
        avg_return_20d=round(avg_20d, 2),
        avg_return_60d=0,  # Would need more data
        avg_rsi=round(avg_rsi, 1),
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        momentum_score=round(momentum_score, 1),
        momentum_trend=momentum_trend,
        top_stocks=top_stocks,
        bottom_stocks=bottom_stocks,
    )


def analyze_all_sectors(max_workers: int = 3) -> list[SectorMetrics]:
    """
    Analyze all sectors.

    Returns:
        List of SectorMetrics, sorted by momentum score
    """
    results = []

    for sector in ALL_SECTORS:
        print(f"Analyzing {sector}...")
        metrics = analyze_sector(sector, max_workers=max_workers)
        results.append(metrics)

    # Sort by momentum score (highest first)
    results.sort(key=lambda x: x.momentum_score, reverse=True)

    return results


def get_sector_rotation_signals(sector_metrics: list[SectorMetrics]) -> dict:
    """
    Identify sector rotation signals.

    Args:
        sector_metrics: List of SectorMetrics from analyze_all_sectors()

    Returns:
        dict with rotation signals and recommendations
    """
    if not sector_metrics:
        return {"error": "No sector data available"}

    # Sectors gaining momentum
    gaining = [s for s in sector_metrics if s.momentum_trend == "gaining"]

    # Sectors losing momentum
    losing = [s for s in sector_metrics if s.momentum_trend == "losing"]

    # Top performing (by 5-day return)
    sorted_by_return = sorted(sector_metrics, key=lambda x: x.avg_return_5d, reverse=True)
    top_performing = sorted_by_return[:3]
    worst_performing = sorted_by_return[-3:]

    # Oversold sectors (potential rotation into)
    oversold = [s for s in sector_metrics if s.avg_rsi < 40]

    # Overbought sectors (potential rotation out)
    overbought = [s for s in sector_metrics if s.avg_rsi > 60]

    # Generate recommendations
    recommendations = []

    if gaining:
        top_gain = gaining[0]
        recommendations.append(
            f"ROTATE INTO: {top_gain.sector} sector is gaining momentum "
            f"(score: {top_gain.momentum_score}, 5D return: {top_gain.avg_return_5d}%)"
        )

    if losing:
        top_loss = losing[-1] if losing else None
        if top_loss:
            recommendations.append(
                f"ROTATE OUT: {top_loss.sector} sector is losing momentum "
                f"(score: {top_loss.momentum_score}, 5D return: {top_loss.avg_return_5d}%)"
            )

    if oversold:
        recommendations.append(
            f"WATCH: {', '.join(s.sector for s in oversold)} sectors are oversold (potential bounce)"
        )

    return {
        "gaining_momentum": [(s.sector, float(s.momentum_score), float(s.avg_return_5d)) for s in gaining],
        "losing_momentum": [(s.sector, float(s.momentum_score), float(s.avg_return_5d)) for s in losing],
        "top_performing": [(s.sector, float(s.avg_return_5d)) for s in top_performing],
        "worst_performing": [(s.sector, float(s.avg_return_5d)) for s in worst_performing],
        "oversold_sectors": [(s.sector, float(s.avg_rsi)) for s in oversold],
        "overbought_sectors": [(s.sector, float(s.avg_rsi)) for s in overbought],
        "recommendations": recommendations,
        "timestamp": datetime.now().isoformat(),
    }


def get_sector_summary_table(sector_metrics: list[SectorMetrics]) -> pd.DataFrame:
    """Convert sector metrics to a summary DataFrame."""
    data = []
    for s in sector_metrics:
        data.append({
            "Sector": s.sector,
            "Momentum": s.momentum_score,
            "Trend": s.momentum_trend,
            "1D %": s.avg_return_1d,
            "5D %": s.avg_return_5d,
            "20D %": s.avg_return_20d,
            "Avg RSI": s.avg_rsi,
            "Bullish": s.bullish_count,
            "Bearish": s.bearish_count,
            "Stocks": s.stock_count,
        })

    return pd.DataFrame(data)


def format_sector_report(sector_metrics: list[SectorMetrics]) -> str:
    """Generate a text report of sector analysis."""
    lines = [
        "=" * 60,
        "SECTOR ROTATION REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 60,
        "",
    ]

    # Sector rankings
    lines.append("SECTOR RANKINGS (by Momentum Score):")
    lines.append("-" * 40)

    for i, s in enumerate(sector_metrics, 1):
        trend_emoji = "" if s.momentum_trend == "gaining" else "" if s.momentum_trend == "losing" else ""
        lines.append(
            f"{i:2}. {s.sector:20} | Score: {s.momentum_score:5.1f} {trend_emoji} | "
            f"5D: {s.avg_return_5d:+6.2f}% | RSI: {s.avg_rsi:5.1f}"
        )

    lines.append("")

    # Rotation signals
    signals = get_sector_rotation_signals(sector_metrics)

    lines.append("ROTATION SIGNALS:")
    lines.append("-" * 40)
    for rec in signals.get("recommendations", []):
        lines.append(f"  {rec}")

    lines.append("")

    # Top stocks by sector
    lines.append("TOP PERFORMERS BY SECTOR:")
    lines.append("-" * 40)
    for s in sector_metrics[:5]:  # Top 5 sectors
        top = ", ".join([f"{t[0]} ({t[1]:+.1f}%)" for t in s.top_stocks[:2]])
        lines.append(f"  {s.sector}: {top}")

    return "\n".join(lines)


def quick_sector_scan() -> dict:
    """
    Quick sector scan returning key metrics.

    Returns simplified data for dashboard display.
    """
    metrics = analyze_all_sectors()
    signals = get_sector_rotation_signals(metrics)

    return {
        "sectors": [
            {
                "name": s.sector,
                "momentum": s.momentum_score,
                "trend": s.momentum_trend,
                "return_5d": s.avg_return_5d,
                "rsi": s.avg_rsi,
                "bullish_ratio": s.bullish_count / s.stock_count if s.stock_count > 0 else 0,
            }
            for s in metrics
        ],
        "signals": signals,
        "timestamp": datetime.now().isoformat(),
    }
