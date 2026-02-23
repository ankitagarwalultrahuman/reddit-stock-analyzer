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
from datetime import datetime, timedelta
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

    # Performance metrics - Monthly timeframes (averaged across stocks)
    avg_return_1w: float = 0.0   # 1 week (5 trading days)
    avg_return_1m: float = 0.0   # 1 month (20 trading days)
    avg_return_2m: float = 0.0   # 2 months (40 trading days)
    avg_return_3m: float = 0.0   # 3 months (60 trading days)
    avg_return_6m: float = 0.0   # 6 months (120 trading days)

    # Legacy aliases for backward compatibility
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
    return_1w: float = 0.0   # 1 week
    return_1m: float = 0.0   # 1 month
    return_2m: float = 0.0   # 2 months
    return_3m: float = 0.0   # 3 months
    return_6m: float = 0.0   # 6 months
    rsi: Optional[float] = None
    technical_bias: str = "neutral"

    # Legacy aliases
    return_1d: float = 0.0
    return_5d: float = 0.0
    return_20d: float = 0.0


def _get_return_for_period(df: pd.DataFrame, calendar_days: int) -> float:
    """
    Calculate return using calendar date lookup with nearest-date fallback.
    This handles trading holidays and weekends correctly.

    Args:
        df: DataFrame with 'Date' and 'Close' columns (Date can be column or index)
        calendar_days: Number of calendar days to look back

    Returns:
        Return as percentage, or 0.0 if not enough data
    """
    if df.empty or len(df) < 2:
        return 0.0

    current = float(df['Close'].iloc[-1])
    if current == 0:
        return 0.0

    # Use 'Date' column if available, otherwise fall back to index
    if 'Date' in df.columns:
        dates = pd.to_datetime(df['Date'])
        last_date = dates.iloc[-1]
        target_date = last_date - timedelta(days=calendar_days)
        mask = dates <= target_date
        if not mask.any():
            return 0.0
        past_price = float(df.loc[mask, 'Close'].iloc[-1])
    else:
        target_date = df.index[-1] - timedelta(days=calendar_days)
        mask = df.index <= target_date
        if not mask.any():
            return 0.0
        past_price = float(df.loc[mask, 'Close'].iloc[-1])

    if past_price == 0:
        return 0.0

    return ((current / past_price) - 1) * 100


def analyze_stock_for_sector(ticker: str, debug: bool = False) -> Optional[StockPerformance]:
    """Analyze a single stock for sector analysis with monthly timeframes."""
    try:
        # Fetch 250 days for 6-month analysis (need 200+ calendar days for 6M return)
        df = fetch_stock_history(ticker, days=250)

        if debug:
            print(f"[DEBUG] {ticker}: df.empty={df.empty}, len={len(df)}, cols={df.columns.tolist() if not df.empty else 'N/A'}")

        if df.empty:
            if debug:
                print(f"[SECTOR] {ticker}: Empty dataframe")
            return None
        if len(df) < 20:
            if debug:
                print(f"[SECTOR] {ticker}: Only {len(df)} rows (need 20+)")
            return None

        # Get technical analysis
        signals = get_technical_analysis(df, ticker)

        if debug:
            print(f"[DEBUG] {ticker}: signals.rsi={signals.rsi}, bias={signals.technical_bias}")

        # Calculate returns - use 'Close' column
        if 'Close' not in df.columns:
            if debug:
                print(f"[SECTOR] {ticker}: No 'Close' column. Columns: {df.columns.tolist()}")
            return None

        close = df['Close']
        current = float(close.iloc[-1])

        # Date-based return calculations (handles holidays/weekends correctly)
        return_1w = _get_return_for_period(df, 7)     # 1 week = 7 calendar days
        return_1m = _get_return_for_period(df, 30)    # 1 month = 30 calendar days
        return_2m = _get_return_for_period(df, 60)    # 2 months = 60 calendar days
        return_3m = _get_return_for_period(df, 90)    # 3 months = 90 calendar days
        return_6m = _get_return_for_period(df, 180)   # 6 months = 180 calendar days

        if debug:
            print(f"[DEBUG] {ticker}: current={current}, 1W={return_1w:.2f}%, 1M={return_1m:.2f}%")

        return StockPerformance(
            ticker=ticker,
            current_price=round(current, 2),
            return_1w=round(float(return_1w), 2),
            return_1m=round(float(return_1m), 2),
            return_2m=round(float(return_2m), 2),
            return_3m=round(float(return_3m), 2),
            return_6m=round(float(return_6m), 2),
            rsi=float(signals.rsi) if signals.rsi else None,
            technical_bias=signals.technical_bias or "neutral",
            # Legacy fields
            return_1d=round(float(return_1w / 5), 2) if return_1w else 0.0,
            return_5d=round(float(return_1w), 2),
            return_20d=round(float(return_1m), 2),
        )

    except Exception as e:
        if debug:
            import traceback
            print(f"[SECTOR] {ticker}: Exception - {type(e).__name__}: {e}")
            print(traceback.format_exc())
        return None


def analyze_sector(sector: str, max_workers: int = 5, use_parallel: bool = True) -> SectorMetrics:
    """
    Analyze all stocks in a sector.

    Args:
        sector: Sector name
        max_workers: Max parallel workers
        use_parallel: Use parallel processing (set False for debugging)

    Returns:
        SectorMetrics object with aggregated data
    """
    stocks = get_sector_stocks(sector)
    if not stocks:
        print(f"[SECTOR] {sector}: No stocks found in watchlist")
        return SectorMetrics(sector=sector, stock_count=0)

    print(f"[SECTOR] {sector}: Analyzing {len(stocks)} stocks...")

    performances = []

    if use_parallel:
        # Analyze stocks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(analyze_stock_for_sector, ticker): ticker
                for ticker in stocks
            }

            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    result = future.result(timeout=30)
                    if result:
                        performances.append(result)
                except Exception as e:
                    print(f"[SECTOR] {ticker}: Future failed - {e}")
    else:
        # Sequential processing (fallback for debugging)
        for ticker in stocks:
            result = analyze_stock_for_sector(ticker)
            if result:
                performances.append(result)

    print(f"[SECTOR] {sector}: {len(performances)}/{len(stocks)} stocks analyzed successfully")

    if not performances:
        print(f"[SECTOR] {sector}: WARNING - No stocks could be analyzed!")
        return SectorMetrics(sector=sector, stock_count=len(stocks))

    # Calculate monthly averages
    avg_1w = sum(p.return_1w for p in performances) / len(performances)
    avg_1m = sum(p.return_1m for p in performances) / len(performances)
    avg_2m = sum(p.return_2m for p in performances) / len(performances)
    avg_3m = sum(p.return_3m for p in performances) / len(performances)
    avg_6m = sum(p.return_6m for p in performances) / len(performances)
    avg_rsi = sum(p.rsi for p in performances if p.rsi) / len([p for p in performances if p.rsi]) if any(p.rsi for p in performances) else 50

    # Count technical biases
    bullish = sum(1 for p in performances if p.technical_bias == "bullish")
    bearish = sum(1 for p in performances if p.technical_bias == "bearish")
    neutral = len(performances) - bullish - bearish

    # Calculate momentum score (0-100)
    # Based on: monthly returns, RSI position, and technical bias ratio
    momentum_score = 50  # Base

    # Return contribution based on 1-month performance (max +/- 25)
    if avg_1m > 0:
        momentum_score += min(avg_1m * 2.5, 25)
    else:
        momentum_score += max(avg_1m * 2.5, -25)

    # RSI contribution (max +/- 15)
    if avg_rsi < 40:
        momentum_score -= 15  # Oversold = losing momentum recently
    elif avg_rsi > 60:
        momentum_score += 15  # Strong momentum

    # Bias contribution (max +/- 10)
    if len(performances) > 0:
        bullish_ratio = bullish / len(performances)
        momentum_score += (bullish_ratio - 0.5) * 20

    # Momentum consistency adjustment
    # Penalize if short-term and long-term returns diverge
    if avg_1w != 0 and avg_1m != 0:
        if (avg_1w > 0) != (avg_1m > 0):
            momentum_score -= 10  # 1W and 1M have opposite signs
    if avg_1w != 0 and avg_1m != 0 and avg_3m != 0:
        if avg_1w > 0 and avg_1m > 0 and avg_3m > 0:
            momentum_score += 5  # All timeframes positively aligned

    momentum_score = max(0, min(100, momentum_score))

    # Determine trend
    if momentum_score > 60:
        momentum_trend = "gaining"
    elif momentum_score < 40:
        momentum_trend = "losing"
    else:
        momentum_trend = "neutral"

    # Sort for top/bottom performers by 1-month return
    sorted_by_return = sorted(performances, key=lambda x: x.return_1m, reverse=True)
    top_stocks = [(p.ticker, float(p.return_1m)) for p in sorted_by_return[:3]]
    bottom_stocks = [(p.ticker, float(p.return_1m)) for p in sorted_by_return[-3:]]

    return SectorMetrics(
        sector=sector,
        stock_count=len(performances),
        # Monthly timeframes
        avg_return_1w=round(avg_1w, 2),
        avg_return_1m=round(avg_1m, 2),
        avg_return_2m=round(avg_2m, 2),
        avg_return_3m=round(avg_3m, 2),
        avg_return_6m=round(avg_6m, 2),
        # Legacy fields for backward compatibility
        avg_return_1d=round(avg_1w / 5, 2) if avg_1w else 0,
        avg_return_5d=round(avg_1w, 2),
        avg_return_20d=round(avg_1m, 2),
        avg_return_60d=round(avg_3m, 2),
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

    # Top performing (by 1-month return)
    sorted_by_return = sorted(sector_metrics, key=lambda x: x.avg_return_1m, reverse=True)
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
            f"(score: {top_gain.momentum_score}, 1M return: {top_gain.avg_return_1m:+.1f}%)"
        )

    if losing:
        top_loss = losing[-1] if losing else None
        if top_loss:
            recommendations.append(
                f"ROTATE OUT: {top_loss.sector} sector is losing momentum "
                f"(score: {top_loss.momentum_score}, 1M return: {top_loss.avg_return_1m:+.1f}%)"
            )

    if oversold:
        recommendations.append(
            f"WATCH: {', '.join(s.sector for s in oversold)} sectors are oversold (potential bounce)"
        )

    return {
        "gaining_momentum": [(s.sector, float(s.momentum_score), float(s.avg_return_1m)) for s in gaining],
        "losing_momentum": [(s.sector, float(s.momentum_score), float(s.avg_return_1m)) for s in losing],
        "top_performing": [(s.sector, float(s.avg_return_1m)) for s in top_performing],
        "worst_performing": [(s.sector, float(s.avg_return_1m)) for s in worst_performing],
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
